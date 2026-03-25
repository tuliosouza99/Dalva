import { useState } from 'react';

interface JsonViewerProps {
  data: Record<string, unknown>;
  dark?: boolean;
}

function JsonNode({ keyName, value, depth = 0, dark }: { keyName: string | null; value: unknown; depth?: number; dark?: boolean }) {
  const [isExpanded, setIsExpanded] = useState(depth < 2);

  if (value === null) {
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        <span style={{ color: dark ? '#f97316' : '#ea580c' }}>null</span>
      </div>
    );
  }

  if (typeof value === 'boolean') {
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        <span style={{ color: dark ? '#a78bfa' : '#8b5cf6' }}>{value.toString()}</span>
      </div>
    );
  }

  if (typeof value === 'number') {
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        <span style={{ color: dark ? '#34d399' : '#10b981' }}>{value}</span>
      </div>
    );
  }

  if (typeof value === 'string') {
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        <span style={{ color: dark ? '#6ee7b7' : '#34d399' }}>"{value}"</span>
      </div>
    );
  }

  if (Array.isArray(value)) {
    const isLong = value.length > 5;
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        {isExpanded ? (
          <>
            <span style={{ color: dark ? '#e5e7eb' : '#374151', cursor: 'pointer' }} onClick={() => setIsExpanded(false)}>▼</span>
            <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}> [</span>
            <div>
              {value.map((item, idx) => (
                <JsonNode key={idx} keyName={null} value={item} depth={depth + 1} dark={dark} />
              ))}
            </div>
            <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}>]</span>
          </>
        ) : (
          <span style={{ color: dark ? '#e5e7eb' : '#374151', cursor: 'pointer' }} onClick={() => setIsExpanded(true)}>▶</span>
        )}
      </div>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value);
    const isLong = entries.length > 5;
    return (
      <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
        <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}>{keyName !== null ? `"${keyName}": ` : ''}</span>
        {isExpanded ? (
          <>
            <span style={{ color: dark ? '#e5e7eb' : '#374151', cursor: 'pointer' }} onClick={() => setIsExpanded(false)}>▼</span>
            <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}> {'{'}</span>
            <div>
              {entries.map(([k, v]) => (
                <JsonNode key={k} keyName={k} value={v} depth={depth + 1} dark={dark} />
              ))}
            </div>
            <span style={{ color: dark ? '#9ca3af' : '#6b7280' }}>{'}'}</span>
          </>
        ) : (
          <span style={{ color: dark ? '#e5e7eb' : '#374151', cursor: 'pointer' }} onClick={() => setIsExpanded(true)}>▶</span>
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
    <div className={`rounded-lg border ${dark ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-200'}`}>
      <div className={`flex items-center justify-between px-4 py-2 border-b ${dark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-100'}`}>
        <span className={`text-sm font-medium ${dark ? 'text-gray-300' : 'text-gray-700'}`}>
          JSON
        </span>
        <button
          onClick={handleCopy}
          className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
            dark
              ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'
          }`}
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className={`p-4 font-mono text-sm overflow-x-auto max-h-96 overflow-y-auto ${dark ? 'text-gray-200' : 'text-gray-800'}`}>
        {Object.entries(data).map(([key, value]) => (
          <JsonNode key={key} keyName={key} value={value} depth={0} dark={dark} />
        ))}
      </div>
    </div>
  );
}
