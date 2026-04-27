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
  const [loading, setLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [url, setUrl] = useState('');
  const [isDemo, setIsDemo] = useState(true);
  const [isSmokeTest, setIsSmokeTest] = useState(false);
  const [selectedPersonas, setSelectedPersonas] = useState(['kid', 'power_user', 'parent', 'retiree']);

  useEffect(() => {
    async function fetchData() {
      try {
        const [bugRes, actRes] = await Promise.all([
          fetch('/api/bugs'),
          fetch('/api/activity')
        ]);
        const bugData = await bugRes.json();
        const actData = await actRes.json();
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
  }, []);

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
    const targetUrl = isDemo ? 'http://localhost:5000' : url;
    
    try {
      // Note: In production, this would be a relative path or env variable
      const res = await fetch('http://localhost:8000/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: targetUrl,
          personas: selectedPersonas,
          is_smoke_test: isSmokeTest,
        }),
      });
      
      if (res.ok) {
        const msg = isSmokeTest 
          ? 'Smoke test started! Skipping mapping and running 1 persona for 5 actions.' 
          : 'Full scan started! Agents are now browsing the target.';
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
    setSelectedPersonas(prev => 
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
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
          <label>Deploy Personas</label>
          <div className="persona-grid">
            {PERSONA_OPTIONS.map(p => (
              <div 
                key={p.id} 
                className={`persona-option ${selectedPersonas.includes(p.id) ? 'active' : ''}`}
                onClick={() => togglePersona(p.id)}
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

        <div className="input-group" style={{marginTop: '2rem', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '12px'}}>
          <div>
            <label style={{marginBottom: 0}}>Smoke Test Mode</label>
            <p className="helper-text" style={{color: 'var(--text-secondary)'}}>Skip mapping, 1 persona, 5 turns (Fast & Cheap)</p>
          </div>
          <input 
            type="checkbox" 
            checked={isSmokeTest} 
            onChange={(e) => setIsSmokeTest(e.target.checked)}
            style={{width: '24px', height: '24px', cursor: 'pointer', accentColor: 'var(--accent-color)'}}
          />
        </div>

        <button 
          className={`primary-btn ${isScanning ? 'loading' : ''}`}
          onClick={handleTriggerScan}
          disabled={isScanning}
        >
          {isScanning ? 'Launching Agents...' : 'Run Parallel Scan'}
        </button>
      </section>

      <div className="section-header">
        <h2>Live Activity</h2>
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

