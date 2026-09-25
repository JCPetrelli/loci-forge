# loci-forge

Build memory palaces (method of loci) in 3D with Blender, the Blender MCP server and Claude.

The method of loci is an old memory technique. You walk through a place you know, in your head, and leave one vivid image at each station along the way. To recall the material you walk the route again. loci-forge makes those places real: you describe a topic, Claude plans the route and the images, and Blender MCP builds the palace so you can walk through it and render it.

## How it works

1. **Topic.** Write down the notions you want to memorize in `topics/`, for example a list, a chapter outline or a set of definitions.
2. **Plan.** Claude turns the topic into an ordered route of loci (rooms, stations, objects) and gives each notion a vivid, unusual image.
3. **Build.** Through the Blender MCP server, Claude builds the palace: architecture, props, lighting, labels and a camera path along the route.
4. **Walk.** Render a fly-through or explore the scene in Blender to rehearse the route.

## Stack

- [Blender](https://www.blender.org/) 4.x
- [blender-mcp](https://github.com/ahujasid/blender-mcp) (`uvx blender-mcp`)
- [Claude Code](https://claude.com/claude-code) with Claude Opus 5.5

## Layout

```
topics/    what to memorize (Markdown)
palaces/   generated .blend scenes and route definitions
scripts/   reusable Blender Python helpers
```

## Status

Early stage. Nothing is built yet.

## License

MIT
