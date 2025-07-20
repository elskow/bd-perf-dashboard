export interface PageLayoutProps {
  children: React.ReactNode;
  title?: string;
  showBackButton?: boolean;
  backButtonText?: string;
  backButtonHref?: string;
  className?: string;
}

export function PageLayout({
  children,
  title,
  showBackButton = false,
  backButtonText = "← Back",
  backButtonHref = "/",
  className = "",
}: PageLayoutProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 text-gray-900 overflow-x-hidden">
      <div
        className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8 min-w-0 overflow-hidden ${className}`}
      >
        {/* Header */}
        {showBackButton && (
          <div className="mb-4 sm:mb-6">
            <a
              href={backButtonHref}
              className="inline-flex items-center text-gray-500 hover:text-gray-700 text-sm transition-colors"
            >
              {backButtonText}
            </a>
          </div>
        )}

        {/* Content */}
        {children}
      </div>
    </div>
  );
}

export function CenteredPageLayout({
  children,
  title,
  className = "",
}: {
  children: React.ReactNode;
  title?: string;
  className?: string;
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 text-gray-900 flex items-center justify-center p-4 overflow-x-hidden">
      <div
        className={`max-w-6xl mx-auto w-full min-w-0 overflow-hidden ${className}`}
      >
        {title && (
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-center text-gray-900 mb-8 sm:mb-12 lg:mb-16 truncate">
            {title}
          </h1>
        )}
        {children}
      </div>
    </div>
  );
}
