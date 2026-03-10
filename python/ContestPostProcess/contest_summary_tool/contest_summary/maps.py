def render_map(df, title, outdir, args):

    if args.map == "countries":
        render_countries_map(df, title, outdir)

    elif args.map == "states_dx":
        render_states_dx_map(df, title, outdir)

    elif args.map == "na_states_dx":
        render_na_states_dx_map(df, title, outdir)


def render_countries_map(df, title, outdir):
    print("Country map not yet implemented")


def render_states_dx_map(df, title, outdir):
    print("States + DX map not yet implemented")


def render_na_states_dx_map(df, title, outdir):
    print("NA states map not yet implemented")