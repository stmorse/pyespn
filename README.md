# pyespn

python espn api wrapper

[good endpoints](https://github.com/pseudo-r/Public-ESPN-API)

[espn-api-orm](https://github.com/theedgepredictor/espn-api-orm/tree/main)


## notes to self

Structure of this effort:

Big picture:
- `schema.yaml` contains scheme of the ESPN API
- `APIGateway` uses the schema to provide a consistent interface to the API
- `League` and `models` are the objects which self-populate using APIGateway