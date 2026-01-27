//! Enumeración y selección de dispositivos de audio.
//!
//! Utiliza cpal para acceder a los dispositivos de entrada del sistema.

use cpal::traits::{DeviceTrait, HostTrait};
use crate::config::AudioDeviceInfo;

/// Enumera todos los dispositivos de entrada de audio disponibles
pub fn list_input_devices() -> anyhow::Result<Vec<AudioDeviceInfo>> {
    let host = cpal::default_host();
    
    // Obtener el dispositivo por defecto para comparar
    let default_device_name = host
        .default_input_device()
        .and_then(|d| d.name().ok());
    
    let devices: Vec<AudioDeviceInfo> = host
        .input_devices()
        .map_err(|e| anyhow::anyhow!("Error enumerando dispositivos: {}", e))?
        .filter_map(|device| {
            let name = device.name().ok()?;
            let is_default = default_device_name
                .as_ref()
                .map(|d| d == &name)
                .unwrap_or(false);
            
            Some(AudioDeviceInfo {
                // Usamos el nombre como ID por simplicidad
                // En una implementación más robusta, usaríamos IDs únicos
                id: name.clone(),
                name,
                is_default,
            })
        })
        .collect();
    
    Ok(devices)
}

/// Obtiene el dispositivo de entrada por defecto
pub fn get_default_input_device() -> anyhow::Result<cpal::Device> {
    let host = cpal::default_host();
    host.default_input_device()
        .ok_or_else(|| anyhow::anyhow!("No hay dispositivo de entrada por defecto disponible"))
}

/// Selecciona un dispositivo de entrada por ID (nombre)
/// Si el ID es None, retorna el dispositivo por defecto
pub fn select_input_device(device_id: Option<&str>) -> anyhow::Result<cpal::Device> {
    let host = cpal::default_host();
    
    match device_id {
        Some(id) => {
            // Buscar el dispositivo por nombre
            host.input_devices()
                .map_err(|e| anyhow::anyhow!("Error enumerando dispositivos: {}", e))?
                .find(|d| d.name().ok().as_deref() == Some(id))
                .ok_or_else(|| anyhow::anyhow!("Dispositivo '{}' no encontrado", id))
        }
        None => get_default_input_device(),
    }
}

/// Obtiene la configuración de entrada soportada por un dispositivo
pub fn get_supported_config(device: &cpal::Device) -> anyhow::Result<cpal::SupportedStreamConfig> {
    device
        .default_input_config()
        .map_err(|e| anyhow::anyhow!("Error obteniendo configuración del dispositivo: {}", e))
}

/// Obtiene información del sample rate y canales de un dispositivo
pub fn get_device_format(device: &cpal::Device) -> anyhow::Result<(u32, u16)> {
    let config = get_supported_config(device)?;
    Ok((config.sample_rate().0, config.channels()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_list_devices() {
        // Este test solo verifica que no hay panic
        // Los dispositivos disponibles dependen del sistema
        let result = list_input_devices();
        assert!(result.is_ok());
    }
}
