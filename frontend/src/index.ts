import index from "./index.html";

const PORT = Number(process.env.PORT || 3000);

const server = Bun.serve({
  port: PORT,
  routes: {
    // Serve the SPA shell (index.html) for every non-asset route so React Router can take over.
    "/*": index,
  },
  development: process.env.NODE_ENV !== "production" && {
    hmr: true,
    console: true,
  },
});

console.log(`🚀 Server running at ${server.url}`);
