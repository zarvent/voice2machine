## 2025-05-23 - [Icon-Only Buttons & Error States]
**Learning:** This app frequently uses icon-only buttons (like '✕' or SVG icons) with `title` attributes but missing `aria-label`. While `title` can provide an accessible name, `aria-label` is more robust and consistent across screen readers. Also, the critical error banner was not marked as a live region.
**Action:** Always check `btn-icon` usage and close buttons (especially those using raw characters like '✕') for `aria-label`. Ensure critical status messages use `role="alert"` and `aria-live`.
