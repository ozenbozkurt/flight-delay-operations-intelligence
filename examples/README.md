# Demonstration data

`demo_flights.csv` contains eight manually constructed, synthetic records with
fictional airport/carrier codes. It is not an extract of actual flight records
and must not be used to make claims about airline performance.

Expected result: seven analyzed flights, one cancelled flight excluded,
three departures strictly over 15 minutes late, mean departure delay
115 / 7 minutes. January has four flights and a late rate of 0.25;
February has three analyzed flights and a late rate of 2 / 3.

The existing `data/` samples and historical `REPORT.md` are separate from this
fixture. Their upstream source and redistribution terms need documenting
before a public packaged release includes those data files.
