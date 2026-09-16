import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';

describe('Shared UI Primitives', () => {
  it('renders button with variants and handles click', () => {
    render(<Button variant="default">Scan Target</Button>);
    expect(screen.getByRole('button', { name: /scan target/i })).toBeInTheDocument();
  });

  it('renders card with header and content', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Security Findings</CardTitle>
        </CardHeader>
        <CardContent>
          <p>No vulnerabilities detected</p>
        </CardContent>
      </Card>
    );
    expect(screen.getByText('Security Findings')).toBeInTheDocument();
    expect(screen.getByText('No vulnerabilities detected')).toBeInTheDocument();
  });

  it('renders badge with appropriate variant styling', () => {
    render(<Badge variant="destructive">Critical</Badge>);
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });


  it('renders empty state with call-to-action', () => {
    render(
      <EmptyState
        title="No Repositories"
        description="Connect your Git repository to begin vulnerability scanning."
        action={<Button>Connect Repository</Button>}
      />
    );
    expect(screen.getByText('No Repositories')).toBeInTheDocument();
    expect(screen.getByText(/connect your git repository/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /connect repository/i })).toBeInTheDocument();
  });

  it('renders error state with retry button', () => {
    render(
      <ErrorState
        title="Failed to Load Data"
        message="Could not reach backend API service."
        onRetry={() => {}}
      />
    );
    expect(screen.getByText('Failed to Load Data')).toBeInTheDocument();
    expect(screen.getByText(/could not reach backend/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });
});
