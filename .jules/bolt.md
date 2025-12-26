## 2024-05-23 - [Implicit Timer State Bottleneck]
**Learning:** Storing high-frequency timers (like `lastPingTime`) in the global state of a React hook (`useBackend`) causes the entire component tree to re-render on every tick (e.g., 500ms), even if the data isn't critical for the UI.
**Action:** Throttling or debouncing state updates for high-frequency but low-priority UI data (like timestamps) preserves functionality while drastically reducing re-renders.
