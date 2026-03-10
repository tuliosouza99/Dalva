import { useState } from 'react';
import { useS3Status, usePushToS3 } from '../api/client';
import { Link } from 'react-router-dom';

export default function S3PushPage() {
  const { data: status, isLoading } = useS3Status();
  const pushMutation = usePushToS3();
  const [showConfirm, setShowConfirm] = useState(false);

  const handlePush = async () => {
    try {
      await pushMutation.mutateAsync();
      setShowConfirm(false);
    } catch (error) {
      console.error('Failed to push to S3:', error);
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
              Please configure your S3 settings before pushing data to S3.
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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Push to S3</h1>
          <p className="text-gray-600">
            Upload your local database to S3. This will overwrite the database stored in S3 with
            your local version.
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

        {/* Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-blue-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">Information</h3>
              <p className="mt-1 text-sm text-blue-700">
                This will backup your local experiments to S3. The upload is verified to ensure
                data integrity. This operation is safe and won't affect your local database.
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
              Push Database to S3
            </button>
          ) : (
            <div className="space-y-3">
              <p className="text-center text-gray-700 font-medium">
                Are you sure you want to push to S3?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handlePush}
                  disabled={pushMutation.isPending}
                  className="flex-1 px-4 py-3 bg-primary-500 text-white rounded-md hover:bg-primary-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {pushMutation.isPending ? 'Pushing...' : 'Yes, Push to S3'}
                </button>
                <button
                  onClick={() => setShowConfirm(false)}
                  disabled={pushMutation.isPending}
                  className="flex-1 px-4 py-3 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {pushMutation.isError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">
                ❌ Error: {(pushMutation.error as Error).message}
              </p>
            </div>
          )}

          {pushMutation.isSuccess && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-800">
                ✅ Database pushed to S3 successfully! Your data is now backed up in the cloud.
              </p>
            </div>
          )}
        </div>

        {/* Usage Tips */}
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-md">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Usage Tips</h3>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
            <li>Push after completing important experiments to back them up</li>
            <li>Push before switching machines to share your data</li>
            <li>The upload is verified automatically to ensure data integrity</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
