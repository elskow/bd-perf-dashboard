export interface LoadingProps {
  text?: string;
}

export function Loading({ text = "Loading..." }: LoadingProps) {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center text-gray-900">
      <div className="flex flex-col items-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
        <div className="text-gray-600 text-base">{text}</div>
      </div>
    </div>
  );
}

export function LoadingCard({ text = "Loading..." }: LoadingProps) {
  return (
    <div className="flex items-center justify-center p-8 text-gray-900">
      <div className="flex flex-col items-center space-y-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        <div className="text-gray-600 text-sm">{text}</div>
      </div>
    </div>
  );
}
