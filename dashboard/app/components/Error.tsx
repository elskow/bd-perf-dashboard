export interface ErrorProps {
  message: string;
  onRetry?: () => void;
}

export function Error({ message, onRetry }: ErrorProps) {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center text-gray-900">
      <div className="flex flex-col items-center space-y-6 max-w-md text-center">
        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 13.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
        </div>
        <div className="text-red-600 font-semibold text-lg">Error</div>
        <div className="text-gray-700 text-base">{message}</div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="bg-gradient-to-r from-red-600 to-pink-600 text-white px-6 py-3 rounded-lg text-base hover:from-red-700 hover:to-pink-700 transition-all duration-300 font-medium shadow-sm"
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  );
}

export function ErrorCard({ message, onRetry }: ErrorProps) {
  return (
    <div className="flex items-center justify-center p-8 text-gray-900">
      <div className="flex flex-col items-center space-y-4 max-w-md text-center">
        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
          <svg
            className="w-5 h-5 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 13.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
        </div>
        <div className="text-red-600 text-base">{message}</div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="bg-gradient-to-r from-red-600 to-pink-600 text-white px-4 py-2 rounded-lg text-sm hover:from-red-700 hover:to-pink-700 transition-all duration-300 font-medium shadow-sm"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
