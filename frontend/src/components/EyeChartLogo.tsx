import { cn } from "@/lib/utils"

interface EyeChartLogoProps {
  className?: string
}

export function EyeChartLogo({ className }: EyeChartLogoProps) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("w-5 h-5", className)}
    >
      <defs>
        <radialGradient id="lg-iris" cx="45%" cy="42%" r="55%">
          <stop offset="0%" stopColor="#c4b5fd" />
          <stop offset="50%" stopColor="#a5b4fc" />
          <stop offset="100%" stopColor="#93c5fd" />
        </radialGradient>
        <radialGradient id="lg-pupil" cx="42%" cy="40%" r="50%">
          <stop offset="0%" stopColor="#7c7cb8" />
          <stop offset="100%" stopColor="#5b5b99" />
        </radialGradient>
        <linearGradient id="lg-glow" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="white" stopOpacity="0.25" />
          <stop offset="100%" stopColor="white" stopOpacity="0.4" />
        </linearGradient>
        <clipPath id="lg-clip">
          <circle cx="32" cy="32" r="14" />
        </clipPath>
      </defs>

      {/* Eye outer shape */}
      <path
        d="M3 32C3 32 14 12 32 12C50 12 61 32 61 32C61 32 50 52 32 52C14 52 3 32 3 32Z"
        fill="#f5f3ff"
      />
      <path
        d="M3 32C3 32 14 12 32 12C50 12 61 32 61 32C61 32 50 52 32 52C14 52 3 32 3 32Z"
        fill="none"
        stroke="#c4b5fd"
        strokeWidth="1.2"
      />

      {/* Iris */}
      <circle cx="32" cy="32" r="14" fill="url(#lg-iris)" />
      <circle cx="32" cy="32" r="14" fill="none" stroke="#ddd6fe" strokeWidth="0.8" opacity="0.6" />

      {/* Pupil (enlarged) */}
      <circle cx="32" cy="32" r="9" fill="url(#lg-pupil)" />

      {/* Chart (clipped to iris) */}
      <g clipPath="url(#lg-clip)">
        {/* Glow */}
        <polyline
          points="19,37 23,35 26,38 30,28 33,31 36,24 40,26 45,19"
          stroke="url(#lg-glow)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        {/* Main line (white) */}
        <polyline
          points="19,37 23,35 26,38 30,28 33,31 36,24 40,26 45,19"
          stroke="white"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          opacity="0.9"
        />
      </g>

      {/* Light reflections */}
      <ellipse
        cx="27" cy="26" rx="3.2" ry="2.2"
        fill="white" opacity="0.45"
        transform="rotate(-15 27 26)"
      />
      <circle cx="37.5" cy="25" r="1.3" fill="white" opacity="0.3" />
    </svg>
  )
}
