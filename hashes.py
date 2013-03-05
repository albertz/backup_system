
# We want to differ between each single unique file (by raw content)
# and between media entities such as the same music song or the same movie.
# Equality on a lower entity-level automatically means equality on a
# higher entity-level.
EntityLevel = ("File", "Media")

class Hash:
	entityLevel = EntityLevel[0]
	name = None
	function = None
	
hashes = [
	Hash(name="sha1"),
	Hash(name="path", function = computer + path),
	Hash(name="sound-acoustid-fingerprint", function = acoustid),	
]
