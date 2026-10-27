# Hallmark demo workbench

Terminal and browser clients for the existing Hallmark proof workflows.
This optional project has its own lockfile; it does not change the inference
environment or install into the core library.

From the repository root:

```sh
make demo-web
make demo-tui
make check-demo
```

The web server listens on `http://127.0.0.1:8765`. A second client joins the
same controller for that checkout. Workflows start only when you request one.

[Usage, architecture, supported workflows and extension contract](../docs/WORKBENCH.md).
