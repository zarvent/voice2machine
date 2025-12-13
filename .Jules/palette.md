## 2025-12-13 - [Accessibility of Critical Feedback]
**Learning:** Error banners are critical for user trust, but without `role="alert"` and `aria-live="assertive"`, screen reader users might miss the context of why the app stopped working. Simple inline changes can drastically improve this without needing a full UI component library.
**Action:** Always wrap error messages in a container with `role="alert"` and `aria-live="assertive"`. Ensure close buttons have `aria-label`.

## 2025-12-13 - [Icon-Only Button Accessibility]
**Learning:** Icon-only buttons (like GitHub links or settings toggles) are visually clean but often lack `aria-label`s, relying only on `title`. `title` is not reliably read by all assistive technologies.
**Action:** Always add `aria-label` to buttons that do not have visible text content. Consider dynamic labels for toggle states (e.g., "Show X" vs "Hide X") for better context.
