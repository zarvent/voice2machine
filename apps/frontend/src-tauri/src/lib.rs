// voice2machine tauri frontend
// comunicación con daemon python via socket unix

use tokio::net::UnixStream;
use tokio::io::{AsyncWriteExt, AsyncReadExt};

const SOCKET_PATH: &str = "/tmp/v2m.sock";

/// envía comando al daemon v2m via socket unix
/// protocolo: 4 bytes length (big-endian) + payload utf-8
#[tauri::command]
async fn send_command(command: String) -> Result<String, String> {
    // 1. conectar al socket
    let mut stream = UnixStream::connect(SOCKET_PATH).await
        .map_err(|e| format!("daemon no corre: {}", e))?;

    // 2. protocolo de framing (mismo que client.py)
    let payload = command.as_bytes();
    let len = (payload.len() as u32).to_be_bytes(); // big endian

    stream.write_all(&len).await.map_err(|e| e.to_string())?;
    stream.write_all(payload).await.map_err(|e| e.to_string())?;

    // 3. leer respuesta (expandido a 16KB para transcripciones largas)
    let mut response_buf = Vec::new();
    let mut buf = [0u8; 4096];
    loop {
        let n = stream.read(&mut buf).await.map_err(|e| e.to_string())?;
        if n == 0 { break; }
        response_buf.extend_from_slice(&buf[..n]);
    }

    let response = String::from_utf8_lossy(&response_buf).to_string();
    Ok(response)
}

/// obtiene estado actual del daemon
#[tauri::command]
async fn get_status() -> Result<String, String> {
    send_command("GET_STATUS".to_string()).await
}

/// inicia grabación de audio
#[tauri::command]
async fn start_recording() -> Result<String, String> {
    send_command("START_RECORDING".to_string()).await
}

/// detiene grabación y transcribe
#[tauri::command]
async fn stop_recording() -> Result<String, String> {
    send_command("STOP_RECORDING".to_string()).await
}

/// verifica si daemon está activo
#[tauri::command]
async fn ping() -> Result<String, String> {
    send_command("PING".to_string()).await
}

/// procesa texto con LLM
#[tauri::command]
async fn process_text(text: String) -> Result<String, String> {
    send_command(format!("PROCESS_TEXT {}", text)).await
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            send_command,
            get_status,
            start_recording,
            stop_recording,
            ping,
            process_text
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
