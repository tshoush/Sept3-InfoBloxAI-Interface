# Changelog

## [2.0.0] - 2025-09-03

### Added
- 🎨 Complete UI redesign with modern, spacious layout
- 🤖 MCP (Model Context Protocol) integration
  - Dynamic WAPI tool discovery
  - Auto-generated tools for all WAPI objects
  - RAG-powered documentation
- 📱 New MCP configuration page
- 🔧 New MCP tools browser page
- 🔍 Real-time status monitoring with auto-refresh
- 💫 Beautiful gradient design and animations
- 🎯 Quick example query buttons with icons
- 📊 Three-panel status dashboard
- 🌐 Enhanced navigation with working links
- 🔒 Secure credential management via environment variables

### Fixed
- ✅ Status checking now properly connects to InfoBlox
- ✅ Navigation links (Query and Config) now working
- ✅ Port management and cleanup issues resolved
- ✅ Authentication with correct credentials (admin/infoblox)
- ✅ Grid Master IP updated to 192.168.1.224

### Changed
- 🔄 Migrated from app_configurable.py to app_mcp_enhanced.py
- 🔄 Improved error handling and user feedback
- 🔄 Enhanced response display with dark theme
- 🔄 Better organization of configuration options

### Technical
- Python 3.8+ compatibility
- Flask web framework
- MCP server integration
- ChromaDB for RAG
- Support for multiple LLM providers

## [1.0.0] - 2025-09-02

### Initial Release
- Basic InfoBlox WAPI integration
- Natural language query processing
- Simple web interface
- Configuration management
- Test suite