'use client';
import { useEffect, useState, useRef } from 'react';

const PERSONA_OPTIONS = [
  { id: 'kid', label: '8-Year-Old', icon: '👶', desc: 'Random clicking, confused.' },
  { id: 'power_user', label: 'Power User', icon: '💻', desc: 'Technical, tries to break things.' },
  { id: 'parent', label: 'Anxious Parent', icon: '🛡️', desc: 'Worried about privacy/safety.' },
  { id: 'retiree', label: 'Retiree', icon: '👓', desc: 'Simplified, high-contrast user.' },
];

const DEMO_APPS = [
  { id: 'shop', label: 'ScriptSim Shop', url: 'http://localhost:5000', icon: '🛒', desc: 'E-commerce store with cart bugs.', email: 'test@scriptsim.com', password: 'TestPass123!' },
  { id: 'jobs', label: 'TalentHub Jobs', url: 'http://localhost:5001', icon: '💼', desc: 'Job board with filtering & crash bugs.', email: 'user@talenthub.com', password: 'JobPass123!' },
  { id: 'doctor', label: 'MediBook Health', url: 'http://localhost:5002', icon: '🏥', desc: 'Doctor booking with IDOR & double booking.', email: 'patient@medibook.com', password: 'HealthPass123!' },
];

export default function Dashboard() {
  const [bugs, setBugs] = useState([]);
  const [activity, setActivity] = useState([]);
  const [scanStatus, setScanStatus] = useState('');
  const [activeScanId, setActiveScanId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [url, setUrl] = useState('');
  const [isDemo, setIsDemo] = useState(true);
  const [selectedDemoApp, setSelectedDemoApp] = useState(DEMO_APPS[0].id);
  const [scanMode, setScanMode] = useState('full'); // 'full', 'smoke', 'fast'
  const [selectedPersonas, setSelectedPersonas] = useState(['kid', 'power_user', 'parent', 'retiree']);
  const [scanSummary, setScanSummary] = useState(null);
  const completionAlertShown = useRef(false);

  useEffect(() => {
    // Don't fetch anything until a scan has been started
    if (!activeScanId) {
      setLoading(false);
      return;
    }

    async function fetchData() {
      try {
        const query = `?scanId=${activeScanId}`;
        const [bugRes, actRes] = await Promise.all([
          fetch(`/api/bugs${query}`, { cache: 'no-store' }),
          fetch(`/api/activity${query}`, { cache: 'no-store' })
        ]);
        const bugData = await bugRes.json();
        const actData = await actRes.json();

        // We must use functional state updates here because useEffect closes over the initial state
        setScanStatus(prevStatus => {
          if (actData.scanStatus === 'completed' && prevStatus === 'running' && !completionAlertShown.current) {
            completionAlertShown.current = true;
            alert('Scan complete! The dashboard now shows the final deduplicated bug report.');
          }
          return actData.scanStatus || prevStatus || '';
        });

        setBugs(bugData.bugs || []);
        setScanSummary(bugData.summary || null);
        setActivity(actData.activity || []);

      } catch (err) {
        console.error('Failed to fetch data', err);
      } finally {
        setLoading(false);
      }
    }

    // Only set up polling if the scan is still running or hasn't started yet
    if (scanStatus !== 'completed') {
      fetchData();
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [activeScanId, scanStatus]);

  const getEstimatedTime = () => {
    const count = selectedPersonas.length;
    let actionTime = 0;
    if (scanMode === 'fast') actionTime = 0.5;
    else if (scanMode === 'smoke') actionTime = 1.25;
    else actionTime = 1.75;
    const totalMins = 1 + actionTime + (count * 0.25);
    return `~${Math.ceil(totalMins * 2) / 2} min`;
  };

  const handleTriggerScan = async () => {
    if (!isDemo && !url) {
      alert('Please enter a target URL.');
      return;
    }
    if (selectedPersonas.length === 0) {
      alert('Please select at least one persona.');
      return;
    }

    setIsScanning(true);
    setBugs([]);
    setActivity([]);
    setActiveScanId(null);
    setScanStatus('running');
    completionAlertShown.current = false;
    setScanSummary(null);

    const selectedApp = DEMO_APPS.find(a => a.id === selectedDemoApp);
    const targetUrl = isDemo ? selectedApp.url : url;

    try {
      const res = await fetch('http://127.0.0.1:8000/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: targetUrl,
          email: isDemo ? selectedApp.email : null,
          password: isDemo ? selectedApp.password : null,
          personas: selectedPersonas,
          scan_mode: scanMode,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setActiveScanId(data.scan_id);

        if (data.status === 'awaiting_login') {
          alert('A browser window is opening on your machine.\n\nPlease log in manually in that browser, then press ENTER in the terminal to start the scan.');
        } else {
          let msg = 'Full scan started! Agents are now browsing the target.';
          if (scanMode === 'fast') msg = `Fast scan started! Running ${selectedPersonas.length} personas.`;
          if (scanMode === 'smoke') msg = `Smoke test started! Running ${selectedPersonas.length} personas.`;
          alert(msg);
        }
      } else {
        const err = await res.json();
        alert(`Error: ${typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail) || 'Failed to start scan'}`);
      }
    } catch (err) {
      alert('Could not connect to ScriptSim API. Make sure start.py is running.');
    } finally {
      setIsScanning(false);
    }
  };

  const togglePersona = (id) => {
    if (scanMode === 'fast' || scanMode === 'smoke') {
      setSelectedPersonas([id]);
    } else {
      setSelectedPersonas(prev =>
        prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
      );
    }
  };

  const handleScanModeChange = (mode) => {
    setScanMode(mode);
    if (mode === 'fast' || mode === 'smoke') {
      setSelectedPersonas(prev => prev.length > 0 ? [prev[0]] : ['kid']);
    }
  };

  return (
    <div className="container">
      <header className="header">
        <h1>ScriptSim</h1>
        <p>AI-Powered Behavioral Accessibility Testing Platform</p>
      </header>

      <section className="card scan-config">
        <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Start New Scan</h2>

        <div className="input-group">
          <label>Target Product</label>
          <div className="toggle-container">
            <button
              className={`toggle-btn ${isDemo ? 'active' : ''}`}
              onClick={() => setIsDemo(true)}
            >
              Demo App
            </button>
            <button
              className={`toggle-btn ${!isDemo ? 'active' : ''}`}
              onClick={() => setIsDemo(false)}
            >
              Live Website
            </button>
          </div>
          {!isDemo && (
            <input
              type="text"
              placeholder="https://your-site.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="url-input"
            />
          )}
          {isDemo && (
            <div className="demo-app-selector" style={{ marginTop: '1rem' }}>
              <label style={{ fontSize: '0.85rem', opacity: 0.7, marginBottom: '0.5rem', display: 'block' }}>Choose Demo Application</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
                {DEMO_APPS.map(app => (
                  <div
                    key={app.id}
                    className={`demo-app-option ${selectedDemoApp === app.id ? 'active' : ''}`}
                    onClick={() => setSelectedDemoApp(app.id)}
                  >
                    <div style={{ fontSize: '1.2rem', marginBottom: '0.25rem' }}>{app.icon}</div>
                    <div style={{ fontWeight: '600', fontSize: '0.9rem' }}>{app.label}</div>
                    <div style={{ fontSize: '0.7rem', opacity: 0.6, marginTop: '0.25rem' }}>{app.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="input-group" style={{ marginTop: '2rem' }}>
          <label>Deploy Personas{(scanMode === 'fast' || scanMode === 'smoke') ? ' (select one)' : ' (select all that apply)'}</label>
          <div className="persona-grid">
            {PERSONA_OPTIONS.map(p => (
              <div
                key={p.id}
                className={`persona-option ${selectedPersonas.includes(p.id) ? 'active' : ''}`}
                onClick={() => togglePersona(p.id)}
                title={(scanMode === 'fast' || scanMode === 'smoke') ? 'Only one persona allowed in this mode' : ''}
              >
                <span className="persona-icon">{p.icon}</span>
                <div className="persona-info">
                  <div className="persona-name">{p.label}</div>
                  <div className="persona-desc">{p.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="input-group" style={{ marginTop: '2rem' }}>
          <label>Scan Mode</label>
          <div className="toggle-container" style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
            <button
              className={`toggle-btn ${scanMode === 'full' ? 'active' : ''}`}
              onClick={() => handleScanModeChange('full')}
              style={{ flex: 1 }}
            >
              Full Scan
            </button>
            <button
              className={`toggle-btn ${scanMode === 'smoke' ? 'active' : ''}`}
              onClick={() => handleScanModeChange('smoke')}
              style={{ flex: 1 }}
            >
              Smoke Test
            </button>
            <button
              className={`toggle-btn ${scanMode === 'fast' ? 'active' : ''}`}
              onClick={() => handleScanModeChange('fast')}
              style={{ flex: 1 }}
            >
              Fast Scan
            </button>
          </div>
          <p className="helper-text" style={{ marginTop: '0.5rem' }}>
            {scanMode === 'full' && 'Runs full mapper and all selected personas for maximum coverage.'}
            {scanMode === 'smoke' && 'Skips mapper, runs 1 persona for 15 actions (Standard).'}
            {scanMode === 'fast' && 'Skips mapper, runs 1 persona for 10 actions (Quick preview).'}
          </p>
        </div>

        <button
          className={`primary-btn ${isScanning ? 'loading' : ''}`}
          onClick={handleTriggerScan}
          disabled={isScanning}
          style={{ marginTop: '2rem' }}
        >
          {isScanning ? 'Launching Agents...' : `Run Scan (${getEstimatedTime()})`}
        </button>
      </section>

      <div className="section-header">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          Live Activity
          {scanStatus === 'running' && <span style={{ fontSize: '0.9rem', color: 'var(--accent-cyan)', fontWeight: 'normal' }}>(Running...)</span>}
          {scanStatus === 'completed' && <span style={{ fontSize: '0.9rem', color: '#10b981', fontWeight: 'normal' }}>(Completed)</span>}
        </h2>
        <span className="count-badge">
          {activity.length} Events
        </span>
      </div>

      <div className="card activity-console">
        {activity.length === 0 ? (
          <p style={{ opacity: 0.5 }}>Waiting for agent activity...</p>
        ) : (
          activity.map((log, i) => (
            <div key={i} className="activity-line">
              <span className="activity-timestamp">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
              <span className="activity-author">{log.author}:</span>
              <span className="activity-msg">{log.message}</span>
            </div>
          ))
        )}
      </div>

      {/* Behavioral Analytics Section */}
      {scanStatus === 'completed' && scanSummary && scanSummary.metrics && (
        <section className="metrics-dashboard" style={{ marginTop: '2rem', marginBottom: '2rem' }}>
          <div className="section-header">
            <h2>🧠 Behavioral Analytics</h2>
            <span className="count-badge" style={{ background: 'rgba(139, 92, 246, 0.1)', color: '#a78bfa', borderColor: '#a78bfa' }}>Inclusion Metrics</span>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1.5rem', fontSize: '0.75rem', opacity: 0.7, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ color: '#10b981' }}>🟢 1-3 (Seamless):</span> Linear path. No backtracking.
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ color: '#f59e0b' }}>🟡 4-6 (Clunky):</span> Minor backtracking or redundant clicks.
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ color: '#ef4444' }}>🔴 7-10 (High Friction):</span> Major loops or UI dead-ends.
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginTop: '1.5rem' }}>
            {scanSummary.metrics.map(m => (
              <div key={m.persona} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>{PERSONA_OPTIONS.find(p => p.id === m.persona)?.icon}</span>
                    <span style={{ fontWeight: '600' }}>{PERSONA_OPTIONS.find(p => p.id === m.persona)?.label}</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', padding: '0.25rem 0.5rem', borderRadius: '4px', background: m.friction_score > 7 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)', color: m.friction_score > 7 ? '#ef4444' : '#10b981', border: '1px solid currentColor' }}>
                    Friction: {m.friction_score}/10
                  </div>
                </div>
                
                <div style={{ display: 'flex', gap: '2rem', marginBottom: '1.5rem' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', opacity: 0.6, textTransform: 'uppercase' }}>Time on Task</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: '700' }}>{(m.time_on_task_seconds || m.time_to_success_seconds || 0)}s</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', opacity: 0.6, textTransform: 'uppercase' }}>Total Actions</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: '700' }}>{m.total_actions}</div>
                  </div>
                </div>

                {m.confusion_areas && m.confusion_areas.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.75rem', fontWeight: '600', marginBottom: '0.5rem', color: '#f59e0b' }}>⚠️ Confusion Areas</div>
                    <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                      {m.confusion_areas.map((area, i) => (
                        <li key={i} style={{ fontSize: '0.8rem', opacity: 0.8, marginBottom: '0.25rem', paddingLeft: '1rem', borderLeft: '2px solid rgba(245, 158, 11, 0.3)' }}>
                          {area}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="section-header">
        <h2>{scanStatus === 'completed' ? 'Final Bug Report' : 'Live Reports'}</h2>
        <span className="count-badge">{bugs.length} Issues Found</span>
      </div>

      {scanStatus === 'completed' && scanSummary && (
        <div className="card" style={{ marginBottom: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem' }}>
            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1.5rem', borderRadius: '1rem', textAlign: 'center', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--text-primary)', lineHeight: 1, marginBottom: '0.5rem' }}>{scanSummary.total_bugs}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Total Bugs</div>
            </div>
            <div style={{ background: 'rgba(239, 68, 68, 0.05)', padding: '1.5rem', borderRadius: '1rem', textAlign: 'center', border: '1px solid rgba(239, 68, 68, 0.1)' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#ef4444', lineHeight: 1, marginBottom: '0.5rem' }}>{scanSummary.critical_count}</div>
              <div style={{ color: '#ef4444', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600, opacity: 0.8 }}>Critical</div>
            </div>
            <div style={{ background: 'rgba(249, 115, 22, 0.05)', padding: '1.5rem', borderRadius: '1rem', textAlign: 'center', border: '1px solid rgba(249, 115, 22, 0.1)' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#f97316', lineHeight: 1, marginBottom: '0.5rem' }}>{scanSummary.major_count}</div>
              <div style={{ color: '#f97316', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600, opacity: 0.8 }}>Major</div>
            </div>
          </div>
          {scanSummary.scan_summary && (
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '1rem', borderLeft: '4px solid var(--accent-cyan)' }}>
              <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--accent-cyan)', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI Executive Summary</h4>
              <p style={{ margin: 0, opacity: 0.85, fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--text-secondary)' }}>{scanSummary.scan_summary}</p>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="loading-state">
          <p>Connecting to Firestore...</p>
        </div>
      ) : (
        <div className="bug-grid">
          {bugs.map((bug, i) => {
            const personaLabel = bug.personas_affected?.join(', ') || bug.persona || 'unknown';
            const title = bug.title || (bug.description ? bug.description.split('\n')[0].split('.')[0] : 'Bug found');
            const severityLabel = bug.severity_label || `Sev ${bug.severity}`;
            const rank = bug.rank;
            return (
              <div key={i} className="card bug-card">
                <div className="bug-header">
                  <span className="persona-tag">
                    {rank ? `#${rank} · ` : ''}{personaLabel}
                  </span>
                  {scanStatus === 'completed' && (
                    <span className={`severity-badge severity-${bug.severity}`}>
                      {severityLabel}
                    </span>
                  )}
                </div>
                <h3 className="bug-title">{title}</h3>
                <p className="bug-desc">{bug.description}</p>

                {(bug.steps_to_reproduce || bug.expected_behavior || bug.actual_behavior) && (
                  <details className="bug-details">
                    <summary>
                      <span style={{flex: 1}}>Technical Details</span>
                      <span style={{fontSize: '1.2em', lineHeight: 1}}>▾</span>
                    </summary>
                    <div className="bug-details-content">
                      {bug.steps_to_reproduce && (
                        <div className="bug-details-section">
                          <h4>Steps to reproduce</h4>
                          <div style={{ whiteSpace: 'pre-line', opacity: 0.85 }}>{bug.steps_to_reproduce}</div>
                        </div>
                      )}
                      
                      {bug.expected_behavior && (
                        <div className="bug-details-section">
                          <h4>Expected Behavior</h4>
                          <div style={{ opacity: 0.85 }}>{bug.expected_behavior}</div>
                        </div>
                      )}
                      
                      {bug.actual_behavior && (
                        <div className="bug-details-section">
                          <h4>Actual Behavior</h4>
                          <div style={{ opacity: 0.85 }}>{bug.actual_behavior}</div>
                        </div>
                      )}
                    </div>
                  </details>
                )}

                {bug.url && (
                  <div className="bug-url">
                    <span style={{ opacity: 0.5 }}>URL:</span> {bug.url}
                  </div>
                )}

                {bug.signed_screenshot_url && (
                  <div className="screenshot-container">
                    <img
                      src={bug.signed_screenshot_url}
                      alt="Evidence"
                      className="screenshot"
                      onClick={() => window.open(bug.signed_screenshot_url, '_blank')}
                    />
                    <div className="screenshot-hint">Click to expand screenshot</div>
                  </div>
                )}
              </div>
            );
          })}
          {bugs.length === 0 && (
            <div className="empty-state">
              <p>No active bugs reported. Run a scan to deploy agents.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}