"use client";

import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Hook for managing auto-scroll behavior with manual scroll detection
 * 
 * When user scrolls up, auto-scroll is disabled and a "Jump to latest" pill is shown.
 * Auto-scroll resumes when user scrolls back to bottom or clicks the pill.
 */
export function useAutoScroll<T extends HTMLElement = HTMLDivElement>({
  isStreaming,
  threshold = 100, // pixels from bottom to consider "at bottom"
}: {
  isStreaming: boolean;
  threshold?: number;
}) {
  const containerRef = useRef<T>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);
  const userScrolledRef = useRef(false);

  // Check if user is at bottom
  const checkIfAtBottom = useCallback(() => {
    const container = containerRef.current;
    if (!container) return true;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    return distanceFromBottom <= threshold;
  }, [threshold]);

  // Scroll to bottom
  const scrollToBottom = useCallback((smooth = true) => {
    const container = containerRef.current;
    if (!container) return;

    container.scrollTo({
      top: container.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto',
    });

    userScrolledRef.current = false;
    setIsAtBottom(true);
    setShowJumpToLatest(false);
  }, []);

  // Handle scroll event
  const handleScroll = useCallback(() => {
    const atBottom = checkIfAtBottom();
    setIsAtBottom(atBottom);

    // If user manually scrolled up while streaming, show jump to latest
    if (!atBottom && isStreaming && userScrolledRef.current) {
      setShowJumpToLatest(true);
    } else if (atBottom) {
      setShowJumpToLatest(false);
    }
  }, [checkIfAtBottom, isStreaming]);

  // Track user scroll events
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let scrollTimeout: NodeJS.Timeout;

    const onScroll = () => {
      userScrolledRef.current = true;
      
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        handleScroll();
      }, 100); // Debounce scroll events
    };

    container.addEventListener('scroll', onScroll, { passive: true });

    return () => {
      container.removeEventListener('scroll', onScroll);
      clearTimeout(scrollTimeout);
    };
  }, [handleScroll]);

  // Auto-scroll when streaming and user hasn't manually scrolled up
  useEffect(() => {
    if (isStreaming && isAtBottom && !userScrolledRef.current) {
      scrollToBottom(false); // Instant scroll during streaming
    }
  }, [isStreaming, isAtBottom, scrollToBottom]);

  // Initial scroll to bottom
  useEffect(() => {
    scrollToBottom(false);
  }, [scrollToBottom]);

  return {
    containerRef,
    isAtBottom,
    showJumpToLatest,
    scrollToBottom,
  };
}
