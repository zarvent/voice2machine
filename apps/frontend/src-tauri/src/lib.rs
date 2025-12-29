// Aprende más sobre comandos de Tauri en https://tauri.app/v1/guides/features/command

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::process::Command as SysCommand;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use tauri::path::BaseDirectory;
use tauri::Manager;

// --- CONSTANTES DE SEGURIDAD (SEIKETSU/SAFETY) ---

/// Tamaño máximo de respuesta permitido (1MB) para prevenir ataques de memoria (DoS).
const MAX_RESPONSE_SIZE: usize = 1024 * 1024;

/// Timeout de lectura para evitar bloqueos infinitos (en segundos).
const READ_TIMEOUT_SECS: u64 = 5;

// --- ESTRUCTURAS DE DATOS ---

/// Estructura para enviarle comandos al daemon.
/// Sigue el protocolo JSON-IPC v2.0.
#[derive(Serialize)]
struct IpcCommand {
    /// Nombre del comando (ej: "GET_STATUS")
    /// NOTA: El campo se llama 'cmd' para coincidir con IPCRequest de Python
    cmd: String,
    /// Datos opcionales (payload)
    data: Option<Value>,
}

/// Respuesta estandarizada del daemon.
#[derive(Deserialize, Debug)]
struct DaemonResponse {
    /// Estado de la operación ("success" o "error")
    #[allow(dead_code)]
    status: String,
    /// Mensaje descriptivo o datos de retorno
    data: Option<Value>,
    /// Mensaje de error si status == "error"
    error: Option<String>,
}

// --- FUNCIONES CORE ---

/// Obtiene la ruta segura del socket, replicando la lógica de Python.
/// Utiliza OnceLock para resolver la ruta una sola vez y evitar overhead de exec.
fn get_socket_path() -> &'static Path {
    static SOCKET_PATH: OnceLock<PathBuf> = OnceLock::new();

    SOCKET_PATH.get_or_init(|| {
        // 1. Try XDG_RUNTIME_DIR
        if let Ok(xdg_runtime) = std::env::var("XDG_RUNTIME_DIR") {
            return Path::new(&xdg_runtime).join("v2m").join("v2m.sock");
        }

        // 2. Fallback to /tmp with user-specific subdirectory
        // Usamos el comando 'id' para obtener el UID si no podemos usar libc
        let uid_output = SysCommand::new("id")
            .arg("-u")
            .output()
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
            .unwrap_or_else(|_| "1000".to_string()); // Fallback default (seguro fallar que crash)

        let app_name = "v2m";
        std::env::temp_dir().join(format!("{}_{}", app_name, uid_output)).join("v2m.sock")
    })
}

/// Envía una solicitud JSON al daemon Python a través de un socket Unix.
///
/// # Argumentos
/// * `command` - El comando a ejecutar (ej: "START_RECORDING").
/// * `data` - Payload opcional en formato JSON.
///
/// # Retorno
/// Retorna `Result<Value, String>` con la respuesta del daemon o un error descriptivo.
///
/// # Seguridad
/// Implementa framing (4 bytes length header) y límites de tamaño de respuesta.
fn send_json_request(command: &str, data: Option<Value>) -> Result<Value, String> {
    // 1. Conexión al Socket
    let socket_path = get_socket_path();

    // Intentamos conectar al archivo del socket Unix.
    let mut stream = UnixStream::connect(socket_path)
        .map_err(|e| format!("No se pudo conectar al daemon en {:?} (¿está corriendo?): {}", socket_path, e))?;

    // Configurar timeouts para evitar que la UI se congele si el backend muere.
    stream
        .set_read_timeout(Some(std::time::Duration::from_secs(READ_TIMEOUT_SECS)))
        .map_err(|e| format!("Falló al setear timeout: {}", e))?;

    // 2. Preparación del Payload
    let request = IpcCommand {
        cmd: command.to_string(),
        data,
    };
    let json_payload = serde_json::to_string(&request)
        .map_err(|e| format!("Error serializando JSON: {}", e))?;

    let payload_bytes = json_payload.as_bytes();
    let payload_len = payload_bytes.len() as u32;

    // 3. Envío con Framing (Length-Prefix)
    // Primero enviamos 4 bytes indicando el tamaño del mensaje.
    // Esto asegura que el backend sepa exactamente cuánto leer.
    stream
        .write_all(&payload_len.to_be_bytes())
        .map_err(|e| format!("Error escribiendo header: {}", e))?;

    // Luego enviamos el cuerpo del mensaje.
    stream
        .write_all(payload_bytes)
        .map_err(|e| format!("Error escribiendo payload: {}", e))?;

    // 4. Lectura de Respuesta
    // Leemos los primeros 4 bytes para saber el tamaño de la respuesta.
    let mut len_buf = [0u8; 4];
    stream
        .read_exact(&mut len_buf)
        .map_err(|e| format!("Error leyendo header de respuesta (¿backend caído?): {}", e))?;

    let response_len = u32::from_be_bytes(len_buf) as usize;

    // CHECK DE SEGURIDAD: Validar que el tamaño no exceda el límite.
    if response_len > MAX_RESPONSE_SIZE {
        return Err(format!(
            "La respuesta del daemon excede el límite de seguridad ({} MB)",
            MAX_RESPONSE_SIZE / (1024 * 1024)
        ));
    }

    // Leemos el payload exacto
    let mut response_buf = vec![0u8; response_len];
    stream
        .read_exact(&mut response_buf)
        .map_err(|e| format!("Error leyendo cuerpo de respuesta: {}", e))?;

    // 5. Deserialización
    let response_str = String::from_utf8(response_buf)
        .map_err(|e| format!("Respuesta invalida UTF-8: {}", e))?;

    let response: DaemonResponse = serde_json::from_str(&response_str)
        .map_err(|e| format!("Daemon retornó JSON inválido: {}", e))?;

    // Verificar estado lógico
    if response.status == "success" {
        Ok(response.data.unwrap_or(Value::Null))
    } else {
        Err(response.error.unwrap_or_else(|| "Error desconocido del daemon".to_string()))
    }
}

// --- COMANDOS TAURI (EXPOSED TO FRONTEND) ---

/// Comando: Obtener estado actual del sistema.
#[tauri::command]
fn get_status() -> Result<String, String> {
    let res = send_json_request("GET_STATUS", None)?;
    // Retornamos el JSON como string para que el frontend lo parsee tipado
    Ok(res.to_string())
}

/// Comando: START_RECORDING
#[tauri::command]
fn start_recording() -> Result<String, String> {
    send_json_request("START_RECORDING", None).map(|v| v.to_string())
}

/// Comando: STOP_RECORDING
#[tauri::command]
fn stop_recording() -> Result<String, String> {
    send_json_request("STOP_RECORDING", None).map(|v| v.to_string())
}

/// Comando: PING (Verificar conectividad)
#[tauri::command]
fn ping() -> Result<String, String> {
    send_json_request("PING", None).map(|v| v.to_string())
}

/// Comando: PROCESS_TEXT (Refinar texto con LLM)
#[tauri::command]
fn process_text(text: String) -> Result<String, String> {
    let data = json!({ "text": text });
    send_json_request("PROCESS_TEXT", Some(data)).map(|v| v.to_string())
}

/// Comando: PAUSE_DAEMON
#[tauri::command]
fn pause_daemon() -> Result<String, String> {
    send_json_request("PAUSE_DAEMON", None).map(|v| v.to_string())
}

/// Comando: RESUME_DAEMON
#[tauri::command]
fn resume_daemon() -> Result<String, String> {
    send_json_request("RESUME_DAEMON", None).map(|v| v.to_string())
}

/// Comando: UPDATE_CONFIG
#[tauri::command]
fn update_config(updates: Value) -> Result<String, String> {
    send_json_request("UPDATE_CONFIG", Some(updates)).map(|v| v.to_string())
}

/// Comando: GET_CONFIG
#[tauri::command]
fn get_config() -> Result<String, String> {
    send_json_request("GET_CONFIG", None).map(|v| v.to_string())
}

/// Helper: Resuelve la ruta al script del daemon.
/// En desarrollo usa ruta relativa al proyecto, en producción usa recursos bundled.
fn resolve_daemon_script(app: &tauri::AppHandle) -> Result<std::path::PathBuf, String> {
    // Intentar ruta de desarrollo primero (relativa al proyecto)
    let dev_path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent() // src-tauri -> frontend
        .and_then(|p| p.parent()) // frontend -> apps
        .and_then(|p| p.parent()) // apps -> v2m (raíz del proyecto)
        .map(|p| p.join("scripts/v2m-daemon.sh"));

    if let Some(path) = dev_path.filter(|p| p.exists()) {
        Ok(path)
    } else {
        // Fallback a recursos bundled (producción)
        app.path()
            .resolve("scripts/v2m-daemon.sh", BaseDirectory::Resource)
            .map_err(|e| format!("Error resolviendo ruta del script: {}", e))
    }
}

/// Comando: RESTART_DAEMON (Reinicia el daemon)
#[tauri::command]
async fn restart_daemon(app: tauri::AppHandle) -> Result<String, String> {
    let script_path = resolve_daemon_script(&app)?;

    let output = SysCommand::new("bash")
        .arg(&script_path)
        .arg("restart")
        .output()
        .map_err(|e| format!("Error ejecutando script de reinicio: {}", e))?;

    if output.status.success() {
        Ok("Daemon reiniciado correctamente".to_string())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Fallo al reiniciar daemon: {}", stderr))
    }
}

/// Comando: SHUTDOWN_DAEMON (Detiene el daemon)
#[tauri::command]
async fn shutdown_daemon(app: tauri::AppHandle) -> Result<String, String> {
    let script_path = resolve_daemon_script(&app)?;

    let output = SysCommand::new("bash")
        .arg(&script_path)
        .arg("stop")
        .output()
        .map_err(|e| format!("Error ejecutando script de apagado: {}", e))?;

    if output.status.success() {
        Ok("Daemon detenido correctamente".to_string())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Fallo al detener daemon: {}", stderr))
    }
}

// --- ENTRY POINT ---

/// Configuración inicial de la aplicación Tauri.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_status,
            start_recording,
            stop_recording,
            ping,
            process_text,
            pause_daemon,
            resume_daemon,
            update_config,
            get_config,
            restart_daemon,
            shutdown_daemon
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
