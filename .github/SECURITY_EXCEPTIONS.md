# Temporary dependency security exception

## Vite 5.2.8

- Scope: local uni-app build and development tooling only.
- Reason: `@dcloudio/vite-plugin-uni@3.0.0-5020420260813003` declares an exact `vite@5.2.8` peer dependency. Moving to Vite 6 without a matching DCloud release is not a supported combination.
- Mitigation: the development server is not exposed publicly; production delivers the compiled WeChat mini-program, not the Vite development server or H5 site. All other currently reported high-severity transitive findings are overridden to fixed versions.
- Enforcement: `scripts/check_npm_audit.py` fails CI for any critical finding or high-severity finding outside the named Vite exception.
- Review deadline: 2026-10-31, or immediately when DCloud publishes a compatible patched toolchain.
