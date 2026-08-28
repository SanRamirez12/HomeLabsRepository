with stock_prices as (

    select * from {{ ref('stg_stock_prices') }}

),

with_previous_close as (

    select
        ticker,
        price_date,
        close_price,

        -- LAGS
        -- particionado por ticker (cada acción calcula su propio "día anterior")
        lag(close_price) over (
            partition by ticker
            order by price_date
        ) as previous_close_price

    from stock_prices

),

daily_returns as (

    select
        ticker,
        price_date,
        close_price,
        previous_close_price,

        -- Retorno diario en porcentaje:
        -- (precio_hoy - precio_ayer) / precio_ayer * 100
        round(
            (close_price - previous_close_price) / previous_close_price * 100,
            2
        ) as daily_return_pct

    from with_previous_close

    -- El primer día de cada ticker no tiene "día anterior", así que
    -- previous_close_price sería NULL -- lo excluimos para evitar
    -- errores de división por NULL
    where previous_close_price is not null

)

select * from daily_returns