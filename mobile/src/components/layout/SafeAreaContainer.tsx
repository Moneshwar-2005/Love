import React from 'react';

interface SafeAreaContainerProps {
  children: React.ReactNode;
  className?: string;
  topOnly?: boolean;
  bottomOnly?: boolean;
}

export const SafeAreaContainer: React.FC<SafeAreaContainerProps> = ({
  children,
  className = '',
  topOnly = false,
  bottomOnly = false,
}) => {
  let safeClass = 'pt-[env(safe-area-inset-top,0px)] pb-[env(safe-area-inset-bottom,0px)]';
  if (topOnly) {
    safeClass = 'pt-[env(safe-area-inset-top,0px)]';
  } else if (bottomOnly) {
    safeClass = 'pb-[env(safe-area-inset-bottom,0px)]';
  }

  return (
    <div className={`w-full h-full flex flex-col ${safeClass} ${className}`}>
      {children}
    </div>
  );
};
