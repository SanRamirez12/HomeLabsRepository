with source as (

    select * from {{ source('raw', 'stock_prices') }}

),

renamed as (

    select
        id                  as price_id,
        ticker,
        date                as price_date,
        open                as open_price,
        high                as high_price,
        low                 as low_price,
        close               as close_price,
        volume,
        dividends,
        stock_splits,
        extracted_at

    from source

)

select * from renamed