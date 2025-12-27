# Bolt's Journal

## 2024-05-22 - Initial Journal Creation
**Learning:** Journal created to track performance learnings.
**Action:** Always check this journal before starting work.

## 2024-05-22 - Frontend Polling Optimization
**Learning:** Frequent polling (500ms) can cause excessive root-level re-renders if the polled state (even a timestamp) is unconditionally updated in the React state.
**Action:** Throttle non-critical state updates (like "last ping time") to a slower interval (e.g., 5s) while keeping the actual data polling frequent. Use `useRef` to track the last update time without triggering re-renders.
