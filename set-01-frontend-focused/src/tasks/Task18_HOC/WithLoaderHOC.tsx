import React, { useState, useEffect, type ComponentType } from 'react';

// Define the props that will be injected into the wrapped component
export interface WithLoadingProps {
  isLoading: boolean;
}

// Define dummy user data
export interface UserData {
  name: string;
  email: string;
}

// Create the HOC
export const withLoading = <P extends object>(
  WrappedComponent: ComponentType<P & WithLoadingProps>
) => {
  // Return a new functional component
  const WithLoadingComponent: React.FC<P> = (props) => {
    const [isLoading, setIsLoading] = useState<boolean>(true);
    
    // Simulate loading with useEffect
    useEffect(() => {
      const timer = setTimeout(() => {
        setIsLoading(false);
      }, 2000); // Simulate a 2-second loading time
      
      return () => {
        clearTimeout(timer);
      };
    }, []);
    
    // Spinner component for loading state
    const LoadingSpinner = () => (
      <div className="flex items-center justify-center h-full w-full">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
    
    // If loading, show the spinner
    if (isLoading) {
      return <LoadingSpinner />;
    }
    
    // Otherwise, render the wrapped component with all its props plus the loading state
    return <WrappedComponent {...props} isLoading={isLoading} />;
  };
  
  // Set display name for debugging purposes
  const wrappedComponentName = WrappedComponent.displayName || WrappedComponent.name || 'Component';
  WithLoadingComponent.displayName = `withLoading(${wrappedComponentName})`;
  
  return WithLoadingComponent;
};

