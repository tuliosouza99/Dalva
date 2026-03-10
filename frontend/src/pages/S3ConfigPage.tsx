import { useState, useEffect } from 'react';
import { useS3Config, useS3Status, useUpdateS3Config } from '../api/client';

export default function S3ConfigPage() {
  const { data: status, isLoading: statusLoading } = useS3Status();
  const { data: config, isLoading: configLoading } = useS3Config();
  const updateConfigMutation = useUpdateS3Config();

  const [bucket, setBucket] = useState('');
  const [key, setKey] = useState('trackai.duckdb');
  const [region, setRegion] = useState('us-east-1');

  useEffect(() => {
    if (config) {
      setBucket(config.bucket || '');
      setKey(config.key || 'trackai.duckdb');
      setRegion(config.region || 'us-east-1');
    }
  }, [config]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateConfigMutation.mutateAsync({ bucket, key, region });
    } catch (error) {
      console.error('Failed to update S3 config:', error);
    }
  };

  if (statusLoading || configLoading) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto">
          <p className="text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">S3 Configuration</h1>
          <p className="text-gray-600">
            Configure your S3 storage settings for database synchronization.
          </p>
        </div>

        {/* Status Card */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Current Status</h2>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Configuration Status:</span>
              <span
                className={`text-sm font-medium ${
                  status?.configured ? 'text-green-600' : 'text-yellow-600'
                }`}
              >
                {status?.configured ? 'Configured' : 'Not Configured'}
              </span>
            </div>
            {status?.configured && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">AWS Credentials:</span>
                <span
                  className={`text-sm font-medium ${
                    status?.credentials_valid ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {status?.credentials_valid ? 'Valid' : 'Invalid'}
                </span>
              </div>
            )}
            {!status?.credentials_valid && status?.configured && (
              <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <p className="text-sm text-yellow-800">
                  ⚠️ AWS credentials are not configured or invalid. Please set{' '}
                  <code className="bg-yellow-100 px-1 rounded">AWS_ACCESS_KEY_ID</code> and{' '}
                  <code className="bg-yellow-100 px-1 rounded">AWS_SECRET_ACCESS_KEY</code>{' '}
                  environment variables.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Configuration Form */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">S3 Settings</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="bucket" className="block text-sm font-medium text-gray-700 mb-1">
                S3 Bucket Name *
              </label>
              <input
                type="text"
                id="bucket"
                value={bucket}
                onChange={(e) => setBucket(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="my-trackai-bucket"
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                The S3 bucket where your database will be stored
              </p>
            </div>

            <div>
              <label htmlFor="key" className="block text-sm font-medium text-gray-700 mb-1">
                S3 Object Key
              </label>
              <input
                type="text"
                id="key"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="trackai.duckdb"
              />
              <p className="mt-1 text-xs text-gray-500">
                The path/filename for the database file in S3
              </p>
            </div>

            <div>
              <label htmlFor="region" className="block text-sm font-medium text-gray-700 mb-1">
                AWS Region
              </label>
              <input
                type="text"
                id="region"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="us-east-1"
              />
              <p className="mt-1 text-xs text-gray-500">The AWS region where your bucket is located</p>
            </div>

            <div className="pt-4">
              <button
                type="submit"
                disabled={updateConfigMutation.isPending}
                className="w-full px-4 py-2 bg-primary-500 text-white rounded-md hover:bg-primary-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {updateConfigMutation.isPending ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>

            {updateConfigMutation.isError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">
                  ❌ Error: {(updateConfigMutation.error as Error).message}
                </p>
              </div>
            )}

            {updateConfigMutation.isSuccess && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                <p className="text-sm text-green-800">
                  ✅ Configuration saved successfully!
                </p>
              </div>
            )}
          </form>
        </div>

        {/* Instructions */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">Next Steps</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm text-blue-800">
            <li>Ensure AWS credentials are set in your environment</li>
            <li>Save your S3 configuration above</li>
            <li>Use S3 Pull to download existing data or S3 Push to upload your local database</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
