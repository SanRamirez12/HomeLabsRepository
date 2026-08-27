with stock_prices as (

    select * from {{ ref('stg_stock_prices') }}

),

rolling_average as (

    select
        ticker,
        price_date,
        close_price,

        -- Media móvil de 7 días: promedio del precio de cierre
        -- considerando la fila actual y las 6 anteriores (7 en total),
        -- particionado por ticker para no mezclar acciones distintas.
        round(
            avg(close_price) over (
                partition by ticker
                order by price_date
                rows between 6 preceding and current row
            ),
            2
        ) as moving_avg_7d

    from stock_prices

)

select * from rolling_average
order by ticker, price_date