use pyo3::prelude::*;
use numpy::PyArray1;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::sync::Arc;
use log::{error, info};
use sysinfo::System;
use rubato::{Resampler, SincFixedIn, SincInterpolationType, SincInterpolationParameters, WindowFunction};

// --- ARQUITECTURA SOTA (STATE OF THE ART) ---
// Audio: Lock-Free Ring Buffer (ringbuf).
// Resampling: Band-limited Sinc Interpolation (rubato).
// Monitoring: Native Syscalls (sysinfo).

/// AudioRecorder implementation in Rust using Lock-Free Ring Buffer + High Quality Resampling.
#[pyclass(unsendable)]
struct AudioRecorder {
    stream: Option<cpal::Stream>,
    // In ringbuf 0.3, split() returns structs that hold the Arc. We don't need to hold HeapRb manually.
    // The consumer holds the Arc internally.
    consumer: Option<ringbuf::Consumer<f32, Arc<ringbuf::HeapRb<f32>>>>,

    requested_sample_rate: u32,
    device_sample_rate: u32,
    channels: u16,
    is_recording: bool,
}

#[pymethods]
impl AudioRecorder {
    #[new]
    #[pyo3(signature = (sample_rate=16000, channels=1))]
    fn new(sample_rate: u32, channels: u16) -> Self {
        let _ = pyo3_log::try_init();

        AudioRecorder {
            stream: None,
            consumer: None,
            requested_sample_rate: sample_rate,
            device_sample_rate: 0,
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

        // Get supported configs
        let supported_configs = match device.supported_input_configs() {
            Ok(c) => c,
            Err(e) => return Err(pyo3::exceptions::PyOSError::new_err(format!("Failed to query device configs: {}", e))),
        };

        // Select best config
        // Strategy: Prioritize channel match. If rate doesn't match, we will resample.
        // We pick the Max sample rate supported by the device to ensure highest quality source for downsampling.
        let best_config_range = supported_configs.into_iter()
            .filter(|c| c.channels() == self.channels)
            .max_by_key(|c| c.max_sample_rate());

        let config: cpal::StreamConfig = match best_config_range {
            Some(c) => {
                // Use the highest available rate within the supported range, or 48k/44.1k if available,
                // but usually just picking a standard one is fine.
                // Let's pick the closest to requested, or higher.
                let req_rate = cpal::SampleRate(self.requested_sample_rate);
                let target_rate = if c.min_sample_rate() <= req_rate && c.max_sample_rate() >= req_rate {
                    req_rate
                } else {
                    // If requested not supported, pick max (usually 48k or 96k) for best quality
                    c.max_sample_rate()
                };

                self.device_sample_rate = target_rate.0;
                c.with_sample_rate(target_rate).into()
            },
            None => {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    format!("No supported config found for {} channels", self.channels)
                ));
            }
        };

        info!("Starting recording: Requested={}Hz, Device={}Hz", self.requested_sample_rate, self.device_sample_rate);

        // Allocate buffer (approx 10 mins at device rate)
        let buffer_size = (self.device_sample_rate * 60 * 10) as usize;
        let rb = ringbuf::HeapRb::<f32>::new(buffer_size);
        let (mut producer, consumer) = rb.split();

        self.consumer = Some(consumer);

        let err_fn = move |err| {
            error!("Audio stream error: {}", err);
        };

        let stream = device.build_input_stream(
            &config,
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                let _ = producer.push_slice(data);
            },
            err_fn,
            None
        ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to build input stream: {}", e)))?;

        stream.play().map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to start stream: {}", e)))?;

        self.stream = Some(stream);
        self.is_recording = true;

        Ok(())
    }

    fn stop<'py>(&mut self, py: Python<'py>) -> PyResult<&'py PyArray1<f32>> {
        if !self.is_recording {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("Not recording"));
        }

        self.stream = None;
        self.is_recording = false;

        let mut raw_data = Vec::new();
        if let Some(consumer) = &mut self.consumer {
            for sample in consumer.pop_iter() {
                raw_data.push(sample);
            }
        }
        self.consumer = None;

        // Resample if necessary
        let final_data = if self.device_sample_rate != self.requested_sample_rate && !raw_data.is_empty() {
            info!("Resampling from {}Hz to {}Hz", self.device_sample_rate, self.requested_sample_rate);

            // rubato SincFixedIn
            let params = SincInterpolationParameters {
                sinc_len: 256,
                f_cutoff: 0.95,
                interpolation: SincInterpolationType::Linear,
                oversampling_factor: 256,
                window: WindowFunction::BlackmanHarris2,
            };

            let f_ratio = self.requested_sample_rate as f64 / self.device_sample_rate as f64;
            let mut resampler = SincFixedIn::<f32>::new(
                f_ratio,
                256.0, // max_resample_ratio_relative (standard value)
                params,
                raw_data.len(), // max input len
                1, // channels
            ).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Resampler init failed: {}", e)))?;

            let waves = vec![raw_data];
            let resampled_waves = resampler.process(&waves, None)
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Resampling failed: {}", e)))?;

            resampled_waves[0].clone()
        } else {
            raw_data
        };

        Ok(PyArray1::from_vec(py, final_data))
    }
}

/// SystemMonitor implementation in Rust.
#[pyclass]
struct SystemMonitor {
    sys: System,
}

#[pymethods]
impl SystemMonitor {
    #[new]
    fn new() -> Self {
        SystemMonitor {
            sys: System::new_all(),
        }
    }

    fn update(&mut self) {
        self.sys.refresh_cpu();
        self.sys.refresh_memory();
    }

    fn get_ram_usage(&self) -> (u64, u64, f32) {
        let total = self.sys.total_memory();
        let used = self.sys.used_memory();
        // Calculate percent manually if needed, or just return values
        // sysinfo doesn't store percent for RAM, we calc it
        let percent = if total > 0 { (used as f64 / total as f64) * 100.0 } else { 0.0 };
        (total, used, percent as f32)
    }

    fn get_cpu_usage(&self) -> f32 {
        self.sys.global_cpu_info().cpu_usage()
    }
}

#[pymodule]
fn v2m_engine(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<AudioRecorder>()?;
    m.add_class::<SystemMonitor>()?;
    Ok(())
}
