/**
 * UI utility components used across pages.
 * These are presentational (stateless) components that rely entirely on props
 * and CSS classes for layout/styling.
 */


/**
 * PageHeader
 * Renders a top section with a title, optional subtitle, and optional right-side actions.
 *
 * Props:
 * - title: main heading text
 * - subtitle: optional descriptive text under the title
 * - right: optional React node (e.g., buttons, controls) rendered on the right side
 */
export function PageHeader({ title, subtitle, right }) {
  return (
    <div className="panel hero">
      <div className="heroLeft">
        <h1 className="heroTitle">{title}</h1>

        {/* Conditionally render subtitle only if provided */}
        {subtitle && <p className="heroText">{subtitle}</p>}
      </div>

      {/* Right-side actions container (only rendered if content exists) */}
      {right && <div className="heroActions">{right}</div>}
    </div>
  );
}


/**
 * KPI (Key Performance Indicator)
 * Displays a labeled metric with optional subtext.
 *
 * Props:
 * - label: descriptor for the metric
 * - value: main numeric/string value
 * - sub: optional secondary/contextual info (e.g., trend, delta)
 */
export function KPI({ label, value, sub }) {
  return (
    <div className="panel kpi">
      <div className="kpiTop">
        {/* Label/header for the KPI */}
        <div className="kpiLabel">{label}</div>
      </div>

      {/* Primary metric value */}
      <div className="kpiValue">{value}</div>

      {/* Optional subtext (conditionally rendered) */}
      {sub ? <div className="kpiSub">{sub}</div> : null}
    </div>
  );
}


/**
 * Alert
 * Simple wrapper for alert/notification content.
 * Uses children prop to allow flexible content injection.
 */
export function Alert({ children }) {
  return <div className="alert">{children}</div>;
}


/**
 * Field
 * Wrapper for form inputs with a label.
 *
 * Props:
 * - label: text label for the field
 * - children: input/control element(s)
 *
 * Note: Does not handle accessibility (e.g., htmlFor/id linkage) yet.
 */
export function Field({ label, children }) {
  return (
    <div className="field">
      <label>{label}</label>

      {/* Input/control passed in from parent */}
      {children}
    </div>
  );
}