'use client';
import { useEffect, useState } from 'react';

const PERSONA_OPTIONS = [
  { id: 'kid', label: '8-Year-Old', icon: '👶', desc: 'Random clicking, confused.' },
  { id: 'power_user', label: 'Power User', icon: '💻', desc: 'Technical, tries to break things.' },
  { id: 'parent', label: 'Anxious Parent', icon: '🛡️', desc: 'Worried about privacy/safety.' },
  { id: 'retiree', label: 'Retiree', icon: '👓', desc: 'Simplified, high-contrast user.' },
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
  const [scanMode, setScanMode] = useState('full'); // 'full', 'smoke', 'fast'
  const [selectedPersonas, setSelectedPersonas] = useState(['kid', 'power_user', 'parent', 'retiree']);

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
          if (actData.scanStatus === 'completed' && prevStatus === 'running') {
            alert('Scan complete! The dashboard now shows the final deduplicated bug report.');
          }
          return actData.scanStatus || '';
        });
        
        setBugs(bugData.bugs || []);
        setActivity(actData.activity || []);
        
      } catch (err) {
        console.error('Failed to fetch data', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [activeScanId]);

  const getEstimatedTime = () => {
    const count = selectedPersonas.length;
    // Base time: ~1 min (setup, synthesis, eval)
    // Parallel persona time: ~0.25 min per action
    // Sequential reporting time: ~0.25 min per persona
    
    let actionTime = 0;
    if (scanMode === 'fast') actionTime = 0.5; // 2 actions * 0.25
    else if (scanMode === 'smoke') actionTime = 1.25; // 5 actions * 0.25
    else actionTime = 1.75; // 7 actions * 0.25
    
    const totalMins = 1 + actionTime + (count * 0.25);
    
    // Round to nearest half minute for display
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
    setScanStatus('running');
    
    const targetUrl = isDemo ? 'http://localhost:5000' : url;
    
    try {
      // Note: In production, this would be a relative path or env variable
      const res = await fetch('http://127.0.0.1:8000/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: targetUrl,
          personas: selectedPersonas,
          scan_mode: scanMode,
        }),
      });
      
      if (res.ok) {
        const data = await res.json();
        setActiveScanId(data.scan_id);
        
        let msg = 'Full scan started! Agents are now browsing the target.';
        if (scanMode === 'fast') msg = `Fast scan started! Running ${selectedPersonas.length} personas for 2 actions each.`;
        if (scanMode === 'smoke') msg = `Smoke test started! Running ${selectedPersonas.length} personas for 5 actions each.`;
        alert(msg);
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Failed to start scan'}`);
      }
    } catch (err) {
      alert('Could not connect to ScriptSim API. Make sure start.py is running.');
    } finally {
      setIsScanning(false);
    }
  };


  const togglePersona = (id) => {
    if (scanMode === 'fast' || scanMode === 'smoke') {
      // Single-select for fast/smoke modes
      setSelectedPersonas([id]);
    } else {
      setSelectedPersonas(prev =>
        prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
      );
    }
  };

  const handleScanModeChange = (mode) => {
    setScanMode(mode);
    // When switching to fast/smoke, keep only the first selected persona
    if (mode === 'fast' || mode === 'smoke') {
      setSelectedPersonas(prev => prev.length > 0 ? [prev[0]] : ['kid']);
    }
  };

  return (
    <div className="container">
      <header className="header">
        <h1>ScriptSim</h1>
        <p>AI-Powered Parallel QA Testing</p>
      </header>

      <section className="card scan-config">
        <h2 style={{marginBottom: '1.5rem', fontSize: '1.5rem'}}>Start New Scan</h2>
        
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
            <p className="helper-text">Using local Flask demo app (port 5000) with pre-planted bugs.</p>
          )}
        </div>

        <div className="input-group" style={{marginTop: '2rem'}}>
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

        <div className="input-group" style={{marginTop: '2rem'}}>
          <label>Scan Mode</label>
          <div className="toggle-container" style={{display: 'flex', gap: '1rem', marginTop: '0.5rem'}}>
            <button 
              className={`toggle-btn ${scanMode === 'full' ? 'active' : ''}`}
              onClick={() => handleScanModeChange('full')}
              style={{flex: 1}}
            >
              Full Scan
            </button>
            <button 
              className={`toggle-btn ${scanMode === 'smoke' ? 'active' : ''}`}
              onClick={() => handleScanModeChange('smoke')}
              style={{flex: 1}}
            >
              Smoke Test
            </button>
            <button 
              className={`toggle-btn ${scanMode === 'fast' ? 'active' : ''}`}
              onClick={() => handleScanModeChange('fast')}
              style={{flex: 1}}
            >
              Fast Scan
            </button>
          </div>
          <p className="helper-text" style={{marginTop: '0.5rem'}}>
            {scanMode === 'full' && 'Runs full mapper and all selected personas for maximum coverage.'}
            {scanMode === 'smoke' && 'Skips mapper, runs 1 persona for 15 actions (Standard).'}
            {scanMode === 'fast' && 'Skips mapper, runs 1 persona for 10 actions (Quick preview).'}
          </p>
        </div>

        <button 
          className={`primary-btn ${isScanning ? 'loading' : ''}`}
          onClick={handleTriggerScan}
          disabled={isScanning}
          style={{marginTop: '2rem'}}
        >
          {isScanning ? 'Launching Agents...' : `Run Scan (${getEstimatedTime()})`}
        </button>
      </section>

      <div className="section-header">
        <h2 style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
          Live Activity 
          {scanStatus === 'running' && <span style={{fontSize: '0.9rem', color: 'var(--accent-color)', fontWeight: 'normal'}}>(Running...)</span>}
          {scanStatus === 'completed' && <span style={{fontSize: '0.9rem', color: '#10b981', fontWeight: 'normal'}}>(Completed)</span>}
        </h2>
        <span className="count-badge" style={{background: 'rgba(59, 130, 246, 0.1)', color: 'var(--accent-color)', borderColor: 'var(--accent-color)'}}>
          {activity.length} Events
        </span>
      </div>

      <div className="card activity-console">
        {activity.length === 0 ? (
          <p style={{opacity: 0.5}}>Waiting for agent activity...</p>
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

      <div className="section-header">
        <h2>Live Reports</h2>
        <span className="count-badge">{bugs.length} Issues Found</span>
      </div>

      {loading ? (
        <div className="loading-state">
          <p>Connecting to Firestore...</p>
        </div>
      ) : (
        <div className="bug-grid">
          {bugs.map((bug, i) => (
            <div key={i} className="card bug-card">
              <div className="bug-header">
                <span className="persona-tag">{bug.persona} found a bug:</span>
                <span className={`severity-badge severity-${bug.severity}`}>
                  Sev {bug.severity}
                </span>
              </div>
              <h3 className="bug-title">{bug.title}</h3>
              <p className="bug-desc">{bug.description}</p>
              
              <div className="bug-meta">
                <p><strong>Impact:</strong> {bug.expected_behavior ? `Expected ${bug.expected_behavior} but got ${bug.actual_behavior}` : 'UX failure'}</p>
                <p style={{marginTop: '0.5rem', opacity: 0.7}}><strong>URL:</strong> {bug.url}</p>
              </div>

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
          ))}
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