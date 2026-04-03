import { useState } from 'react';

interface JsonViewerProps {
  data: Record<string, unknown>;
  dark?: boolean;
}

function JsonNode({ keyName, value, depth = 0, dark }: { keyName: string | null; value: unknown; depth?: number; dark?: boolean }) {
  const [isExpanded, setIsExpanded] = useState(depth < 2);

  const keyColor = dark ? 'var(--text-secondary)' : 'var(--text-secondary)';
  const nullColor = dark ? '#f97316' : '#ea580c';
  const booleanColor = dark ? '#a78bfa' : '#8b5cf6';
  const numberColor = dark ? 'var(--accent)' : 'var(--accent)';
  const stringColor = dark ? '#6ee7b7' : '#059669';
  const punctuationColor = dark ? 'var(--text-tertiary)' : 'var(--text-tertiary)';

  if (value === null) {
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: keyColor }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        <span style={{ color: nullColor }}>null</span>
      </div>
    );
  }

  if (typeof value === 'boolean') {
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: keyColor }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        <span style={{ color: booleanColor }}>{value.toString()}</span>
      </div>
    );
  }

  if (typeof value === 'number') {
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: keyColor }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        <span style={{ color: numberColor }}>{value}</span>
      </div>
    );
  }

  if (typeof value === 'string') {
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: keyColor }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        <span style={{ color: stringColor }}>"{value}"</span>
      </div>
    );
  }

  if (Array.isArray(value)) {
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: keyColor }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        {isExpanded ? (
          <>
            <span style={{ color: 'var(--text-primary)', cursor: 'pointer' }} onClick={() => setIsExpanded(false)}>▼</span>
            <span style={{ color: punctuationColor }}> [</span>
            <div>
              {value.map((item, idx) => (
                <JsonNode key={idx} keyName={null} value={item} depth={depth + 1} dark={dark} />
              ))}
            </div>
            <span style={{ color: punctuationColor }}>]</span>
          </>
        ) : (
          <span style={{ color: 'var(--text-primary)', cursor: 'pointer' }} onClick={() => setIsExpanded(true)}>▶ [...]</span>
        )}
      </div>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: keyColor }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        {isExpanded ? (
          <>
            <span style={{ color: 'var(--text-primary)', cursor: 'pointer' }} onClick={() => setIsExpanded(false)}>▼</span>
            <span style={{ color: punctuationColor }}> {'{'}</span>
            <div>
              {entries.map(([k, v]) => (
                <JsonNode key={k} keyName={k} value={v} depth={depth + 1} dark={dark} />
              ))}
            </div>
            <span style={{ color: punctuationColor }}>{'}'}</span>
          </>
        ) : (
          <span style={{ color: 'var(--text-primary)', cursor: 'pointer' }} onClick={() => setIsExpanded(true)}>▶ {'{...}'}</span>
        )}
      </div>
    );
  }

  return null;
}

export default function JsonViewer({ data, dark = false }: JsonViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div 
      className="rounded-lg border overflow-hidden"
      style={{ 
        backgroundColor: 'var(--bg-primary)', 
        borderColor: 'var(--border)'
      }}
    >
      <div 
        className="flex items-center justify-between px-4 py-2 border-b"
        style={{ 
          backgroundColor: 'var(--bg-surface)', 
          borderColor: 'var(--border)'
        }}
      >
        <span 
          className="text-sm font-medium"
          style={{ color: 'var(--text-secondary)' }}
        >
          JSON
        </span>
        <button
          onClick={handleCopy}
          className="px-3 py-1 text-xs font-medium rounded transition-colors"
          style={{
            backgroundColor: 'var(--bg-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)'
          }}
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div 
        className="p-4 font-mono text-sm overflow-x-auto max-h-96 overflow-y-auto"
        style={{ color: 'var(--text-primary)' }}
      >
        {Object.entries(data).map(([key, value]) => (
          <JsonNode key={key} keyName={key} value={value} depth={0} dark={dark} />
        ))}
      </div>
    </div>
  );
}
