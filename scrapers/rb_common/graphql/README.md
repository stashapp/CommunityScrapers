# Common GraphQL

## Base Class

The base class is currently very basic, it requires the `faraday` gem and the logger for you. From there it defines a `query` method that can take up to two arguments. The first argument is your GraphQL query, and the second argument that defaults to nil if not provided is any variables that you would like to be passed with your query.

It defines a private `logger` method that is just a shorthand of the shared stash logger class `Stash::Logger`.

It defines a `standard_headers` method with:

```Ruby
{
    "Content-Type": "application/json",
    "Accept": "application/json",
    "DNT": "1",
}
```

It is expected that any child classes define an `@extra_headers` variable on initialization with any ApiKey headers or such that may be required.

## Stash Interface

The Stash Interface has been designed so that raw queries should be written in HEREDOC format as private methods like for example:

```Ruby
def gallery_path_query
    <<-'GRAPHQL'
    query FindGallery($id: ID!) {
        findGallery(id: $id) {
            path
        }
    }
    GRAPHQL
end
```

Those raw queries can then be called by any defined public methods like for example:

```Ruby
def get_gallery_path(gallery_id)
    query(gallery_path_query, id_variables(gallery_id))["findGallery"]
end
```

As seem in the above example there is also a private helper method shorthand defined for when the variable passed to the query is just an ID:

```Ruby
def id_variables(id)
    variables = {
        "id": id
    }
end
```
