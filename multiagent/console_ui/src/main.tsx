import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";

import "./index.css";
import { ConsoleApiError } from "./api/client";
import { AuthProvider } from "./auth/AuthProvider";
import { router } from "./router";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Khong thu lai loi 4xx: 401/403/404/422 khong tu khoi phuc, thu lai
      // chi lam nguoi dung cho lau hon roi van thay dung loi do.
      retry: (soLan, error) => {
        if (error instanceof ConsoleApiError && error.status < 500) return false;
        return soLan < 2;
      },
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
