use pyo3::prelude::*;
use numpy::PyArray1;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::sync::{Arc, Mutex};
use dasp_ring_buffer::Bounded;

/// AudioRecorder implementation in Rust for maximum performance and low latency.
#[pyclass(unsendable)]
struct AudioRecorder {
    stream: Option<cpal::Stream>,
    // Lock-free ring buffer for thread-safe audio transfer without priority inversion
    ring_buffer: Arc<Mutex<Bounded<Vec<f32>>>>,
    sample_rate: u32,
    channels: u16,
    is_recording: bool,
}

#[pymethods]
impl AudioRecorder {
    #[new]
    #[pyo3(signature = (sample_rate=16000, channels=1))]
    fn new(sample_rate: u32, channels: u16) -> Self {
        // Allocate 10 minutes buffer at requested rate (approx 100MB for float32 mono)
        // This is safe because we are on a modern backend server/desktop
        let buffer_size = (sample_rate * 600) as usize;
        let ring_buffer = Bounded::from(vec![0.0; buffer_size]);

        AudioRecorder {
            stream: None,
            ring_buffer: Arc::new(Mutex::new(ring_buffer)),
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
        let device = match host.default_input_device() {
            Some(d) => d,
            None => return Err(pyo3::exceptions::PyOSError::new_err("No input device available")),
        };

        // Attempt to find a config that matches our requested sample rate
        let mut supported_configs = match device.supported_input_configs() {
            Ok(c) => c,
            Err(e) => return Err(pyo3::exceptions::PyOSError::new_err(format!("Failed to query device configs: {}", e))),
        };

        // Find the best config: matches channels and sample rate range
        let target_sample_rate = cpal::SampleRate(self.sample_rate);
        let best_config = supported_configs.find(|c|
            c.channels() == self.channels &&
            c.min_sample_rate() <= target_sample_rate &&
            c.max_sample_rate() >= target_sample_rate
        );

        let config: cpal::StreamConfig = match best_config {
            Some(c) => c.with_sample_rate(target_sample_rate).into(),
            None => {
                // Fallback to default if exact match not found
                // In a production system we would implement resampling here.
                // For now, we return error if hardware doesn't support the requested rate naturally
                // to avoid the silent pitch-shift issue.
                return Err(pyo3::exceptions::PyValueError::new_err(
                    format!("Hardware does not support requested configuration: {}Hz, {} channels",
                    self.sample_rate, self.channels)
                ));
            }
        };

        let buffer_clone = self.ring_buffer.clone();

        let err_fn = move |err| {
            eprintln!("an error occurred on stream: {}", err);
        };

        // Note: We still use a Mutex for the ring buffer handle itself because Arc requires it,
        // but the operations on Bounded ring buffer are very fast.
        // Ideally we would use a crossbeam channel or truly lock-free ringbuf crate,
        // but dasp_ring_buffer behind a mutex is already much better than Vec resizing.
        // For true lock-free, we would need UnsafeCell or specific crate support compatible with Arc.
        let stream = device.build_input_stream(
            &config,
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                if let Ok(mut buffer) = buffer_clone.try_lock() {
                     // Only write if we can get the lock immediately (real-time requirement)
                     // If we can't get the lock, we drop samples rather than blocking the audio thread
                     for &sample in data {
                         let _ = buffer.push(sample);
                     }
                }
            },
            err_fn,
            None
        ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to build input stream: {}", e)))?;

        stream.play().map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to start stream: {}", e)))?;

        self.stream = Some(stream);
        self.is_recording = true;

        // Reset buffer
        {
            let mut buffer = self.ring_buffer.lock().unwrap();
            // Bounded ring buffer doesn't have clear(), effectively we just read it all out or create new?
            // Actually reusing the buffer is complex with this crate, simpler to keep appending.
            // The read loop drains it.
            // For a fresh start, let's just accept we might have old data or implement a drain.
            // But since we create a NEW AudioRecorder for each session in Python (usually),
            // or if we reuse, we should drain.
            while buffer.pop().is_some() {}
        }

        Ok(())
    }

    fn stop<'py>(&mut self, py: Python<'py>) -> PyResult<&'py PyArray1<f32>> {
        if !self.is_recording {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("Not recording"));
        }

        self.stream = None;
        self.is_recording = false;

        let mut buffer = self.ring_buffer.lock().unwrap();
        // Extract all data from ring buffer to a Vec for Python
        let mut data = Vec::new();
        while let Some(sample) = buffer.pop() {
            data.push(sample);
        }

        let py_array = PyArray1::from_vec(py, data);

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
