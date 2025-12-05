# build-validator - Extended Documentation

This file contains detailed examples, patterns, and implementation guides for the build-validator agent.

**Load this file when**: You need comprehensive examples, troubleshooting guidance, or deep implementation details.

**Generated**: 2025-12-05

---


## Best Practices

1. **Always Clean First**: Start with `dotnet clean` to avoid cached issues
2. **Check Dependencies**: Run `dotnet list package` before building
3. **Verbose Output**: Use `-v normal` for detailed error messages
4. **Project Isolation**: Test individual projects if solution build fails
5. **Package Versions**: Verify package version compatibility
6. **Platform Specific**: Check conditional compilation for ANDROID/iOS
7. **Incremental Fixes**: Fix one error type at a time

Remember: **No code passes to production if it doesn't compile!**

---