import json
import sys

sys.stdin.read()

print("\x01e\x02", "Deliberately broken scraper", file=sys.stderr, flush=True)

# print(
#     json.dumps(
#         {
#             "title": "A helpful userscript for the queue",
#             "code": "DEMO-123",
#             "date": "2024-02-24",
#             "details": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce vitae quam eros. Mauris et tortor et nibh sodales interdum sed ac neque. Aenean non lectus turpis. Sed fermentum feugiat nunc, in pharetra libero fermentum quis. Integer tempor risus vel finibus sodales. Donec pretium iaculis augue, quis sollicitudin magna interdum ut. Duis convallis fermentum urna vitae congue. Etiam in diam eget lorem congue lacinia quis tempor risus. Ut rutrum mi non ante semper, non maximus enim sagittis. Morbi et finibus est. Nullam eu tristique nibh, sed tincidunt dui. Donec venenatis non nisi eget vulputate. Phasellus non mauris purus. ",
#             "director": "James Movieman",
#             "urls": ["https://demo.rescrape.test/scenes/userscript-demo-scene", "https://members.demo.rescrape.test/paywalled/userscript-demo-scene-4k-ultra"],
#             "studio": {"name": "My Dirty Demo"},
#             "tags": [{"name": "Outdoor"}, {"name": "Pool"}, {"name": "All Natural"}, {"name": "Summer"}, {"name": "Swimsuit"}, {"name": "Beach"}, {"name": "Blonde"}],
#             "performers": [
#                 # Missing ambiguous performer
#                 {"name": "Nicole Sweet"},
#                 # Missing known alias for Angelo Godshack
#                 {"name": "Woody Pepino"},
#                 # Missing unknown alias for Cruella
#                 {"name": "Cruella Naked"},
#                 # Missing performer
#                 {"name": "Oliver Trunk"},
#             ],
#             "image": "https://placehold.co/3840x2160/slategrey/white?text=Example%20cover%20image"
#         }
#     )
# )

