# Climate Intelligence Dashboard Design System

## Product intent

The dashboard is an executive climate-intelligence workspace: scanable in five seconds, traceable to report artifacts, and deep enough for analysts to validate a signal.

## Visual language

- **Canvas:** deep midnight navy `#07111F` with restrained radial gradients.
- **Panels:** translucent navy glass surfaces, 16px radius, one-pixel low-contrast borders, and soft shadows.
- **Electric teal `#28E0C2`:** live metrics, healthy trends, operational status.
- **Neon purple `#A77BFF`:** forecast and AI insight surfaces.
- **Bright cyan `#31C8FF`:** navigation and interactive selection.
- **Amber `#FFB85C`:** warnings, climate signals, and priority findings.
- **Coral `#FF6B7A`:** severe or extreme alerts.
- **Muted grey `#8EA3B8`:** metadata and secondary descriptions.

## Components

`card()` is the primary KPI surface. `section()` creates a consistent title/subtitle rhythm. `insight()` is reserved for derived, traceable interpretations. `chart()` applies the shared Plotly template, responsive sizing, and logo-free controls. Status pills communicate platform state without relying on color alone.

## Interaction principles

Every page exposes a clear first action, keeps filters adjacent to the affected view, and uses the same location/horizon language. Charts use hover labels for detail and tables remain available for auditability. Responsive CSS collapses the visual scale on small screens and Streamlit's native controls preserve keyboard access.

## Trust and accessibility

Color is paired with labels, values, or severity text. Plotly charts use readable fonts, high-contrast foregrounds, and descriptive hover templates. The platform keeps the existing methodological caveats visible: unweighted city observations are not automatically globally representative, and forecast confidence bands are not guarantees.
