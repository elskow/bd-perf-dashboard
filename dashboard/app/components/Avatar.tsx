import { useState } from "react";

export interface AvatarProps {
  name: string;
  image?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Avatar({
  name,
  image,
  size = "md",
  className = "",
}: AvatarProps) {
  const [imageError, setImageError] = useState(false);

  const getInitials = (fullName: string): string => {
    return fullName
      .split(" ")
      .map((word) => word.charAt(0))
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const sizeClasses = {
    sm: "w-10 h-10 text-xs",
    md: "w-14 h-14 text-sm",
    lg: "w-20 h-20 text-base",
  };

  const initials = getInitials(name);

  const shouldShowImage =
    image &&
    typeof image === "string" &&
    image.trim().length > 0 &&
    !imageError;

  if (shouldShowImage) {
    return (
      <img
        src={`data:image/png;base64,${image}`}
        alt={name}
        className={`${sizeClasses[size]} rounded-full object-cover transition-all duration-300 ${className}`}
        onError={() => setImageError(true)}
      />
    );
  }

  return (
    <div
      className={`${sizeClasses[size]} rounded-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center transition-all duration-300 ${className}`}
    >
      <svg
        className="w-full h-full"
        viewBox="0 0 100 100"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient
            id={`avatar-bg-${name.replace(/\s+/g, "")}`}
            x1="0%"
            y1="0%"
            x2="100%"
            y2="100%"
          >
            <stop offset="0%" style={{ stopColor: "#f3f4f6" }} />
            <stop offset="100%" style={{ stopColor: "#e5e7eb" }} />
          </linearGradient>
        </defs>
        <circle
          cx="50"
          cy="50"
          r="50"
          fill={`url(#avatar-bg-${name.replace(/\s+/g, "")})`}
        />
        {initials ? (
          <text
            x="50"
            y="50"
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-gray-600 font-semibold"
            fontSize={size === "sm" ? "20" : size === "md" ? "24" : "28"}
          >
            {initials}
          </text>
        ) : (
          <g fill="#9ca3af">
            <circle cx="50" cy="35" r="12" />
            <path d="M50 50c-13 0-25 8-25 20v10h50V70c0-12-12-20-25-20z" />
          </g>
        )}
      </svg>
    </div>
  );
}
