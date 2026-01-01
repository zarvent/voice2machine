use pyo3::prelude::*;
use numpy::PyArray1;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use ringbuf::{HeapRb, Consumer};
use std::sync::Arc;
use log::{error, info, warn};

// --- ARQUITECTURA SOTA (STATE OF THE ART) ---
// Usamos un Ring Buffer SPSC (Single Producer, Single Consumer).
// Producer: El hilo de audio de alta prioridad (Real-time). NO PUEDE BLOQUEARSE.
// Consumer: El hilo de Python (Main Thread). Puede bloquearse o ser lento.
//
// Esta arquitectura desacopla la captura de audio del procesamiento de Python/GIL.

/// AudioRecorder implementation in Rust using Lock-Free Ring Buffer.
#[pyclass(unsendable)]
struct AudioRecorder {
    // Stream guard must be kept alive to keep recording active
    stream: Option<cpal::Stream>,
    // Consumer end of the ring buffer (owned by Python thread)
    consumer: Option<Consumer<f32, Arc<HeapRb<f32>>>>,
    // Producer end needs to be shared/moved to the stream thread.
    // We store it here temporarily during init or stop, but it lives in the closure during recording.
    // However, since we can't extract it from the closure once moved, we re-create the splitter on start.
    // Actually, `ringbuf` split gives us two separate structs. We hold the consumer here.
    // The producer is moved into the stream closure.
    // To allow `stop` and `start` multiple times, we need to be able to recreate the stream.
    // But `ringbuf` 0.3 split consumes the buffer.
    // Strategy: We create a new ring buffer on every `start()`.

    sample_rate: u32,
    channels: u16,
    is_recording: bool,
}

#[pymethods]
impl AudioRecorder {
    #[new]
    #[pyo3(signature = (sample_rate=16000, channels=1))]
    fn new(sample_rate: u32, channels: u16) -> Self {
        // Inicializar el puente de logs Rust -> Python
        let _ = pyo3_log::try_init();

        AudioRecorder {
            stream: None,
            consumer: None,
            sample_rate,
            channels,
            is_recording: false,
        }
    }

    fn start(&mut self) -> PyResult<()> {
        if self.is_recording {
             return Err(pyo3::exceptions::PyRuntimeError::new_err("Recording already in progress"));
        }

        let host = cpal::default_host();
        // SOTA: Robust Error Handling mapping to Python Exceptions
        let device = match host.default_input_device() {
            Some(d) => d,
            None => {
                warn!("No input device found via CPAL");
                return Err(pyo3::exceptions::PyOSError::new_err("No input device available"));
            }
        };

        // Attempt to find a config that matches our requested sample rate
        let supported_configs = match device.supported_input_configs() {
            Ok(c) => c,
            Err(e) => {
                error!("Failed to query device configs: {}", e);
                return Err(pyo3::exceptions::PyOSError::new_err(format!("Failed to query device configs: {}", e)));
            }
        };

        // SOTA: Explicit Configuration Negotiation
        // We look for a config that strictly matches our needs to avoid hidden resampling issues.
        let target_sample_rate = cpal::SampleRate(self.sample_rate);
        let best_config = supported_configs.into_iter().find(|c|
            c.channels() == self.channels &&
            c.min_sample_rate() <= target_sample_rate &&
            c.max_sample_rate() >= target_sample_rate
        );

        let config: cpal::StreamConfig = match best_config {
            Some(c) => c.with_sample_rate(target_sample_rate).into(),
            None => {
                // If strict match fails, we error out to trigger the Python fallback.
                // This is safer than incorrect implicit behavior.
                warn!("Hardware mismatch: requested {}Hz/{}ch not supported natively", self.sample_rate, self.channels);
                return Err(pyo3::exceptions::PyValueError::new_err(
                    format!("Hardware does not support requested configuration: {}Hz, {} channels",
                    self.sample_rate, self.channels)
                ));
            }
        };

        // --- SOTA: LOCK-FREE RING BUFFER ALLOCATION ---
        // Allocate ~10 mins of audio. HeapRb is allocated on the heap.
        let buffer_size = (self.sample_rate * 60 * 10) as usize;
        let rb = HeapRb::<f32>::new(buffer_size);
        let (mut producer, consumer) = rb.split();

        // Save the consumer for the main thread to read later
        self.consumer = Some(consumer);

        let err_fn = move |err| {
            error!("Audio stream error: {}", err);
        };

        // --- REAL-TIME AUDIO CALLBACK ---
        // This closure runs on a high-priority system thread.
        // CRITICAL RULE: No blocking, no allocating, no syscalls (if possible).
        // pushing to the ringbuf producer is wait-free.
        let stream = device.build_input_stream(
            &config,
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                // SOTA: push_slice is efficient. If buffer is full, it returns count.
                // We ignore the result (drop samples) if full, which is the correct real-time behavior
                // (better to glitch than to crash or block).
                let _ = producer.push_slice(data);
            },
            err_fn,
            None
        ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to build input stream: {}", e)))?;

        stream.play().map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to start stream: {}", e)))?;

        info!("Rust audio stream started at {}Hz", self.sample_rate);
        self.stream = Some(stream);
        self.is_recording = true;

        Ok(())
    }

    fn stop<'py>(&mut self, py: Python<'py>) -> PyResult<&'py PyArray1<f32>> {
        if !self.is_recording {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("Not recording"));
        }

        // 1. Drop stream to stop producer thread
        self.stream = None;
        self.is_recording = false;
        info!("Rust audio stream stopped");

        // 2. Consume data from ring buffer
        // Since producer is dead, we can drain the buffer safely.
        let mut data = Vec::new();
        if let Some(consumer) = &mut self.consumer {
            // SOTA: efficient block read
            // In ringbuf 0.3, we iterate or pop.
            // Converting straight to Vec.
            for sample in consumer.pop_iter() {
                data.push(sample);
            }
        }

        // 3. Convert to efficient NumPy array (Zero-copy optimization possible with PyArray,
        // but from_vec is optimized to use memory view if possible or efficient copy).
        let py_array = PyArray1::from_vec(py, data);

        // Clean up consumer
        self.consumer = None;

        Ok(py_array)
    }

    fn is_recording(&self) -> bool {
        self.is_recording
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn v2m_engine(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<AudioRecorder>()?;
    Ok(())
}
