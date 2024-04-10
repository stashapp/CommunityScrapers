## This scraper reads metadata from a file on Windows using the Shell.Application COM object and outputs it in a format that Stash can understand
## File metadata is stored in the folder object and it's weird as hell

# Read JSON input from stdin
$inputObject = [Console]::In.ReadToEnd() | ConvertFrom-Json


### ALL OF THE BELOW CAN BE REMOVED WHEN STASH SENDS THE FULL METADATA INSTEAD OF JUST THE SCENE ID ###
# We need to make a GraphQL request to get the file path
$filePathQuery = @{ query = "query { findScene(id: `"$($inputObject.id)`") { files { path } } }" } | ConvertTo-Json

# Disgusting horrible hack to find config file in parent directory
$config = Get-Content -Path "../py_common/config.ini" -ErrorAction SilentlyContinue
if ($config) {
    $url = $config | Select-String -Pattern "url = (.*)" | ForEach-Object { $_.Matches.Groups[1].Value }
    if (-not $url) {
        [Console]::Error.WriteLine("$([char]1)w$([char]2) Could not find 'url' in config.ini, defaulting to localhost:9999")
        $url = "http://localhost:9999"
    }
    $api_key = $config | Select-String -Pattern "api_key = (.*)" | ForEach-Object { $_.Matches.Groups[1].Value }
} else {
    [Console]::Error.WriteLine("$([char]1)w$([char]2) Could not read config.ini, defaulting to localhost:9999 with no API key")
    $url = "http://localhost:9999"
    $api_key = ""
}

$filePathResponse = Invoke-WebRequest -Uri "$url/graphql" -Method POST -Body $filePathQuery -ContentType "application/json" -Headers @{ ApiKey = $api_key }

# Ensure the GraphQL request was successful
if ($filePathResponse.StatusCode -ne 200) {
    [Console]::Error.WriteLine("$([char]1)e$([char]2) GraphQL request failed with status code $($filePathResponse.StatusCode): $($filePathResponse.Content)")
    Write-Host "null"
    exit
}

$filePathResponse = $filePathResponse.Content | ConvertFrom-Json

$primaryFile = $filePathResponse.data.findScene.files | Select-Object -First 1 | Select-Object -ExpandProperty path
### END OF DISGUSTING HORRIBLE HACK THAT CAN BE REMOVED ###

# Ensure the file path is provided
if (-not $primaryFile) {
    [Console]::Error.WriteLine("$([char]1)e$([char]2) Could not find a file path for scene '$($inputObject.id)'")
    Write-Host "null"
    exit
}

$file = Get-Item $primaryFile
$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace($file.DirectoryName)
$fileObj = $folder.ParseName($file.Name)

$scraped = New-Object PSObject

# The properties can be enumerated by running the following command:
# 320 is arbitrary, there could be properties with higher indexes! I sure hope these are consistent across Windows versions
# foreach ($i in 0..320) {
#     $name = $folder.GetDetailsOf($folder.Items, $i)
#     $value = $folder.GetDetailsOf($fileObj, $i)
#     Write-Host "$i - $name - $value"
# }


# "Title" has index 21 and we'll output it as "title"
$title = $folder.GetDetailsOf($fileObj, 21)
if ($title) {
    $scraped | Add-Member -MemberType NoteProperty -Name "title" -Value $title
}

# "Publisher" has index 213 and we'll output it as "studio"
$studio = $folder.GetDetailsOf($fileObj, 213)
if ($studio) {
    $scraped | Add-Member -MemberType NoteProperty -Name "studio" -Value @{ name = $studio }
}

# "Media created" has index 208 and we'll output it as "date" after cleaning it and formatting it for Stash
$date = $folder.GetDetailsOf($fileObj, 208)
if ($date) {
    $date = $date.Trim() -replace "[^\x20-\x7E]", "" -split " " | Select-Object -First 1
    $date = [datetime]::Parse($date).ToString("dd-MM-yyyy")
    $scraped | Add-Member -MemberType NoteProperty -Name "date" -Value $date
}

# "Tags" has index 18 and we'll output it as "tags", splitting on semicolon and trimming whitespace
$tags = $folder.GetDetailsOf($fileObj, 18)
if ($tags) {
    # Split on semicolon, trim whitespace, turn into {"name": "tag"} objects
    $tags = $tags -split ";" | % { @{ name = $_.Trim() } }
    $scraped | Add-Member -MemberType NoteProperty -Name "tags" -Value $tags
}

# "Contributing artists" has index 13 and we'll output it as "performers", splitting on semicolon and trimming whitespace
$performers = $folder.GetDetailsOf($fileObj, 13)
if ($performers) {
    # Split on semicolon, trim whitespace, turn into {"name": "performer"} objects
    $performers = $performers -split ";" | % { @{ name = $_.Trim() } }
    $scraped | Add-Member -MemberType NoteProperty -Name "performers" -Value $performers
}

# "Directors" has index 312 and we'll output it as "director", replacing semicolons with comma
$director = $folder.GetDetailsOf($fileObj, 312)
if ($director) {
    $director = $director -replace ";", ","
    $scraped | Add-Member -MemberType NoteProperty -Name "director" -Value $director
}

# "Comments" has index 24 and we'll output it as "details" or maybe "url" if it's a URL
$details = $folder.GetDetailsOf($fileObj, 24)
if ($details) {
    # If the details look like a URL, output it as a URL
    if ($details -match "^https?://") {
        $scraped | Add-Member -MemberType NoteProperty -Name "url" -Value $details
    } else {
        $scraped | Add-Member -MemberType NoteProperty -Name "details" -Value $details
    }
}

# No metadata found
if (($scraped | Get-Member -MemberType Properties | Measure-Object).Count -eq 0) {
    [Console]::Error.WriteLine("$([char]1)d$([char]2) Could not find any metadata for '$($file.FullName)'")
    Write-Host "null"
    exit
}

Write-Host ($scraped | ConvertTo-Json -Compress)
