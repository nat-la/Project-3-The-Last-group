export function PageHeader({ title, subtitle, right }) {
  return (
    <div className="panel hero">
      <div className="heroLeft">
        <h1 className="heroTitle">{title}</h1>
        {subtitle && <p className="heroText">{subtitle}</p>}
      </div>
      {right && <div className="heroActions">{right}</div>}
    </div>
  );
}

export function KPI({ label, value, sub }) {
  return (
    <div className="panel kpi">
      <div className="kpiTop">
        <div className="kpiLabel">{label}</div>
      </div>
      <div className="kpiValue">{value}</div>
      {sub ? <div className="kpiSub">{sub}</div> : null}
    </div>
  );
}

export function Alert({ children }) {
  return <div className="alert">{children}</div>;
}

export function Field({ label, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}