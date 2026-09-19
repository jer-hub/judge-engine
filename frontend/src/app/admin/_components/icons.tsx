type IconProps = {
  className?: string;
  "aria-hidden"?: boolean | "true" | "false";
};

export function ChartBarIcon({ className, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      className={className}
      {...rest}
    >
      <path d="M4 19V10" strokeLinecap="round" />
      <path d="M10 19V5" strokeLinecap="round" />
      <path d="M16 19v-7" strokeLinecap="round" />
      <path d="M22 19H2" strokeLinecap="round" />
    </svg>
  );
}

export function BookIcon({ className, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      className={className}
      {...rest}
    >
      <path
        d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5V5.5Z"
        strokeLinejoin="round"
      />
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" strokeLinecap="round" />
    </svg>
  );
}

export function TrophyIcon({ className, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      className={className}
      {...rest}
    >
      <path d="M8 21h8" strokeLinecap="round" />
      <path d="M12 17v4" strokeLinecap="round" />
      <path d="M7 4h10v5a5 5 0 0 1-10 0V4Z" strokeLinejoin="round" />
      <path d="M7 6H5a2 2 0 0 0 2 4" strokeLinecap="round" />
      <path d="M17 6h2a2 2 0 0 1-2 4" strokeLinecap="round" />
    </svg>
  );
}

export function UsersIcon({ className, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      className={className}
      {...rest}
    >
      <circle cx="9" cy="8" r="3.25" />
      <path d="M3.5 19a5.5 5.5 0 0 1 11 0" strokeLinecap="round" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M15.5 19a4.5 4.5 0 0 1 5-4.2" strokeLinecap="round" />
    </svg>
  );
}

export function MagnifyingGlassIcon({ className, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      className={className}
      {...rest}
    >
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16.5 16.5 21 21" strokeLinecap="round" />
    </svg>
  );
}

export function GearIcon({ className, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      className={className}
      {...rest}
    >
      <circle cx="12" cy="12" r="3" />
      <path
        d="M12 3.5v2.2M12 18.3v2.2M4.9 6.5l1.6 1.5M17.5 16l1.6 1.5M3.5 12h2.2M18.3 12h2.2M4.9 17.5l1.6-1.5M17.5 8l1.6-1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
