import { useState } from 'react';
import { useS3Status, usePullFromS3 } from '../api/client';
import { Link } from 'react-router-dom';

export default function S3PullPage() {
  const { data: status, isLoading } = useS3Status();
  const pullMutation = usePullFromS3();
  const [showConfirm, setShowConfirm] = useState(false);

  const handlePull = async () => {
    try {
      await pullMutation.mutateAsync();
      setShowConfirm(false);
    } catch (error) {
      console.error('Failed to pull from S3:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto">
          <p className="text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  if (!status?.configured) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-yellow-900 mb-2">S3 Not Configured</h2>
            <p className="text-yellow-800 mb-4">
              Please configure your S3 settings before pulling data from S3.
            </p>
            <Link
              to="/s3/config"
              className="inline-block px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 transition-colors"
            >
              Configure S3
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!status?.credentials_valid) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-red-900 mb-2">Invalid AWS Credentials</h2>
            <p className="text-red-800 mb-4">
              Your AWS credentials are not configured or invalid. Please set{' '}
              <code className="bg-red-100 px-1 rounded">AWS_ACCESS_KEY_ID</code> and{' '}
              <code className="bg-red-100 px-1 rounded">AWS_SECRET_ACCESS_KEY</code> environment
              variables and restart the server.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Pull from S3</h1>
          <p className="text-gray-600">
            Download the database from S3 to your local machine. This will replace your local
            database with the version from S3.
          </p>
        </div>

        {/* Configuration Details */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">S3 Configuration</h2>
          <div className="space-y-2 text-sm">
            <div className="flex">
              <span className="text-gray-600 w-24">Bucket:</span>
              <span className="text-gray-900 font-mono">{status.bucket}</span>
            </div>
            <div className="flex">
              <span className="text-gray-600 w-24">Key:</span>
              <span className="text-gray-900 font-mono">{status.key}</span>
            </div>
            <div className="flex">
              <span className="text-gray-600 w-24">Region:</span>
              <span className="text-gray-900 font-mono">{status.region}</span>
            </div>
          </div>
        </div>

        {/* Warning */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-yellow-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">Warning</h3>
              <p className="mt-1 text-sm text-yellow-700">
                This will overwrite your local database. Make sure you have pushed any local
                changes to S3 first if you want to keep them.
              </p>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="bg-white shadow rounded-lg p-6">
          {!showConfirm ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="w-full px-4 py-3 bg-primary-500 text-white rounded-md hover:bg-primary-600 transition-colors font-medium"
            >
              Pull Database from S3
            </button>
          ) : (
            <div className="space-y-3">
              <p className="text-center text-gray-700 font-medium">
                Are you sure you want to pull from S3?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handlePull}
                  disabled={pullMutation.isPending}
                  className="flex-1 px-4 py-3 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {pullMutation.isPending ? 'Pulling...' : 'Yes, Pull from S3'}
                </button>
                <button
                  onClick={() => setShowConfirm(false)}
                  disabled={pullMutation.isPending}
                  className="flex-1 px-4 py-3 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {pullMutation.isError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">
                ❌ Error: {(pullMutation.error as Error).message}
              </p>
            </div>
          )}

          {pullMutation.isSuccess && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-800">
                ✅ Database pulled from S3 successfully! The page will refresh to show the latest
                data.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
