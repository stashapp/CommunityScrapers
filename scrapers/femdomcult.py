import json

# console.log(JSON.stringify($x("//div[@id='torrent_tags']/ul/li/a/text()").map(e => e.textContent)))
tags=[]

res={}
res['tags']=[{"name":x} for x in tags]
print(json.dumps(res))
exit(0)
