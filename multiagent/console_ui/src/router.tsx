import { createBrowserRouter } from "react-router-dom";

import { RequireAuth } from "./auth/RequireAuth";
import { AppShell } from "./layout/AppShell";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { DashboardPage } from "./pages/DashboardPage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobsPage } from "./pages/JobsPage";
import { LoginPage } from "./pages/LoginPage";
import { ReviewDetailPage } from "./pages/ReviewDetailPage";
import { ReviewsPage } from "./pages/ReviewsPage";
import { AuditPage } from "./pages/AuditPage";

export const router = createBrowserRouter(
  [
    { path: "/login", element: <LoginPage /> },
    {
      element: <RequireAuth />,
      children: [
        { path: "/doi-mat-khau", element: <ChangePasswordPage /> },
        {
          element: <AppShell />,
          children: [
            { path: "/", element: <DashboardPage /> },
            { path: "/jobs", element: <JobsPage /> },
            { path: "/jobs/:publicId", element: <JobDetailPage /> },
            { path: "/reviews", element: <ReviewsPage /> },
            { path: "/reviews/:publicId", element: <ReviewDetailPage /> },
            { path: "/audit", element: <AuditPage /> },
          ],
        },
      ],
    },
  ],
  // Phai khop `base` trong vite.config.ts va duong dan mount ben FastAPI.
  { basename: "/console" },
);
