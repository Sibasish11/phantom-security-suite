import type { ReactNode } from "react";
import { Link, Outlet } from "react-router-dom";
import { Logo } from "../components/Logo";

interface PublicLayoutProps {
  children?: ReactNode;
}

export function PublicLayout({
  children,
}: PublicLayoutProps) {
  return (
    <div className="public-layout">
      <header className="public-header">
        <div className="public-header-inner">
          <Link
            to="/"
            className="public-logo-link"
            aria-label="PhantomLayer home"
          >
            <Logo size="medium" />
          </Link>

          <nav className="public-nav">
            <Link to="/how-it-works">
              How it works
            </Link>

            <Link to="/protection">
              Protection
            </Link>
          </nav>

          <div className="public-header-actions">
            <Link
              to="/login"
              className="public-login-link"
            >
              Log in
            </Link>

            <Link
              to="/signup"
              className="public-signup-button"
            >
              Get started
              <span>→</span>
            </Link>
          </div>
        </div>
      </header>

      <main className="public-main">
        {children ?? <Outlet />}
      </main>

      <footer className="public-footer">
        <div className="public-footer-inner">
          <div className="public-footer-brand">
            <Logo
              size="small"
              showText
            />

            <p>
              Intelligent deception infrastructure
              for modern applications.
            </p>
          </div>

          <div className="public-footer-links">
            <div>
              <span>PLATFORM</span>

              <Link to="/how-it-works">
                How it works
              </Link>

              <Link to="/protection">
                Protection
              </Link>
            </div>

            <div>
              <span>ACCOUNT</span>

              <Link to="/login">
                Log in
              </Link>

              <Link to="/signup">
                Get started
              </Link>
            </div>
          </div>
        </div>

        <div className="public-footer-bottom">
          <span>
            © {new Date().getFullYear()} PhantomLayer
          </span>

          <span>
            Security starts with deception.
          </span>
        </div>
      </footer>
    </div>
  );
}