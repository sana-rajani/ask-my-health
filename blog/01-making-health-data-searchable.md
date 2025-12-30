# Making your Apple Health data searchable (no jargon)

You can export a lot of wellness data from Apple Health — but it usually arrives as a big file you don’t want to manually dig through.

This project turns that export into something you can *ask questions* about, like:

- How many steps did I walk this year?
- What were my top 10 walking days?
- Do I walk more on weekdays or weekends?

## The simple idea

Think of it as three parts:

1. **Your export** (the file you already own)
2. **A calculator** (a local database that can total and filter correctly)
3. **A translator** (an AI that turns your question into a query for the calculator)

The key is that the calculator does the math — the AI just translates your question into instructions.

## Privacy (what gets sent where)

This app is designed so your **raw health data stays on your computer**.

If you enable the hosted AI option, the app only sends:

- the *question you typed*
- a short *description of the table columns* (the “schema”)

It does **not** send your Apple Health export or your row-level step data.

## What you’ll do

1. Export your Apple Health data
2. Run the app locally
3. Ask your questions

## What's next

This v1 focuses on **steps only**. Future versions can add sleep, workouts, and more.


