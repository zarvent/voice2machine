// voice2machine tauri frontend
// comunicación con daemon python via socket unix
// PROTOCOLO V2.0 (JSON) - previene command injection

use tokio::net::UnixStream;
use tokio::io::{AsyncWriteExt, AsyncReadExt};
use serde::{Serialize, Deserialize};
use serde_json::json;
use std::process::Command;
use tauri::api::path::resolve_path;
use tauri::Manager;

const SOCKET_PATH: &str = "/tmp/v2m.sock";
const MAX_RESPONSE_SIZE: usize = 1024 * 1024; // 1MB límite (previene DoS/OOM)

/// Request estructurado para el daemon (JSON)
#[derive(Serialize)]
struct IPCRequest {
    cmd: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    data: Option<serde_json::Value>,
}

/// Response estructurada del daemon (JSON)
#[derive(Deserialize, Debug)]
struct IPCResponse {
    status: String,
    data: Option<serde_json::Value>,
    error: Option<String>,
}

/// envía comando estructurado al daemon v2m via socket unix
/// protocolo: 4 bytes length (big-endian) + JSON payload
async fn send_json_request(request: IPCRequest) -> Result<IPCResponse, String> {
    // 1. conectar al socket
    let mut stream = UnixStream::connect(SOCKET_PATH).await
        .map_err(|e| format!("daemon no corre: {}", e))?;

    // 2. serializar request a JSON
    let payload = serde_json::to_string(&request)
        .map_err(|e| format!("error serializando JSON: {}", e))?;
    let payload_bytes = payload.as_bytes();
    let len = (payload_bytes.len() as u32).to_be_bytes(); // big endian

    // 3. enviar con framing (4 bytes length + payload)
    stream.write_all(&len).await.map_err(|e| e.to_string())?;
    stream.write_all(payload_bytes).await.map_err(|e| e.to_string())?;

    // 4. leer respuesta con límite de seguridad (previene OOM)
    let mut response_buf = Vec::new();
    let mut buf = [0u8; 4096];
    loop {
        let n = stream.read(&mut buf).await.map_err(|e| e.to_string())?;
        if n == 0 { break; }

        // SECURITY FIX: verificar límite antes de extender
        if response_buf.len() + n > MAX_RESPONSE_SIZE {
            return Err(format!(
                "respuesta excede el límite de {}MB",
                MAX_RESPONSE_SIZE / (1024 * 1024)
            ));
        }

        response_buf.extend_from_slice(&buf[..n]);
    }

    // 5. parsear JSON response
    let response_json = String::from_utf8(response_buf)
        .map_err(|e| format!("respuesta no es UTF-8 válido: {}", e))?;

    let response: IPCResponse = serde_json::from_str(&response_json)
        .map_err(|e| format!("JSON inválido del daemon: {}", e))?;

    Ok(response)
}

/// Helper para extraer resultado de IPCResponse
fn extract_result(response: IPCResponse) -> Result<String, String> {
    if response.status == "error" {
        return Err(response.error.unwrap_or_else(|| "error desconocido".to_string()));
    }

    // serializar data como JSON string para el frontend
    match response.data {
        Some(data) => Ok(serde_json::to_string(&data).unwrap_or_else(|_| "{}".to_string())),
        None => Ok("{}".to_string()),
    }
}

/// obtiene estado actual del daemon
#[tauri::command]
async fn get_status() -> Result<String, String> {
    let request = IPCRequest {
        cmd: "GET_STATUS".to_string(),
        data: None,
    };
    let response = send_json_request(request).await?;
    extract_result(response)
}

/// inicia grabación de audio
#[tauri::command]
async fn start_recording() -> Result<String, String> {
    let request = IPCRequest {
        cmd: "START_RECORDING".to_string(),
        data: None,
    };
    let response = send_json_request(request).await?;
    extract_result(response)
}

/// detiene grabación y transcribe
#[tauri::command]
async fn stop_recording() -> Result<String, String> {
    let request = IPCRequest {
        cmd: "STOP_RECORDING".to_string(),
        data: None,
    };
    let response = send_json_request(request).await?;
    extract_result(response)
}

/// verifica si daemon está activo
#[tauri::command]
async fn ping() -> Result<String, String> {
    let request = IPCRequest {
        cmd: "PING".to_string(),
        data: None,
    };
    let response = send_json_request(request).await?;
    extract_result(response)
}

/// procesa texto con LLM
/// SECURITY FIX: texto encapsulado en JSON, no concatenado (previene command injection)
#[tauri::command]
async fn process_text(text: String) -> Result<String, String> {
    let request = IPCRequest {
        cmd: "PROCESS_TEXT".to_string(),
        data: Some(json!({"text": text})),
    };
    let response = send_json_request(request).await?;
    extract_result(response)
}

/// pausa el daemon
#[tauri::command]
async fn pause_daemon() -> Result<String, String> {
    let request = IPCRequest {
        cmd: "PAUSE_DAEMON".to_string(),
        data: None,
    };
    let response = send_json_request(request).await?;
    extract_result(response)
}

/// reanuda el daemon
#[tauri::command]
async fn resume_daemon() -> Result<String, String> {
    let request = IPCRequest {
        cmd: "RESUME_DAEMON".to_string(),
        data: None,
    };
    let response = send_json_request(request).await?;
    extract_result(response)
}

/// actualiza configuración del sistema
#[tauri::command]
async fn update_config(updates: serde_json::Value) -> Result<String, String> {
    let request = IPCRequest {
        cmd: "UPDATE_CONFIG".to_string(),
        data: Some(json!({"updates": updates})),
    };
    let response = send_json_request(request).await?;
    extract_result(response)
}

/// obtiene configuración actual
#[tauri::command]
async fn get_config() -> Result<String, String> {
    let request = IPCRequest {
        cmd: "GET_CONFIG".to_string(),
        data: None,
    };
    let response = send_json_request(request).await?;
    extract_result(response)
}

/// reinicia el daemon usando el script v2m-daemon.sh
#[tauri::command]
async fn restart_daemon(app: tauri::AppHandle) -> Result<String, String> {
    let script_path = app.path()
        .resolve("scripts/v2m-daemon.sh", tauri::path::BaseDirectory::Resource)
        .map_err(|e| format!("error resolviendo ruta: {}", e))?;

    let output = Command::new("bash")
        .arg(script_path)
        .arg("restart")
        .output()
        .map_err(|e| format!("error ejecutando script: {}", e))?;

    if output.status.success() {
        Ok("daemon reiniciado".to_string())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("fallo al reiniciar daemon: {}", stderr))
    }
}

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
            restart_daemon
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
