! indicates that rule is forbidden
- indicates that rule will be removed
= indicates that rule is implied
+ indicates that rule will be added

==================================================================
** POWER_CHOICE ** ()
        If this rule is used, players may select an (unspoken for) power to play
        when JOINing the game.  (Without this rule, the DPjudge will assign powers
        to all players randomly.)

==================================================================
** MULTIPLE_POWERS_PER_PLAYER ** ()
        If this rule is used, each player is allowed to control more than 1 power in the game.

==================================================================
** NO_OBSERVATIONS ** ()
        If this rule is used, no observers are allowed for the game. Note that game masters
        can still observe the game as omniscient observers even if this rule is present.

==================================================================
** SOLITAIRE ** (+NO_DEADLINE +CD_DUMMIES +ALWAYS_WAIT)
        A SOLITAIRE game is a game where all powers are dummies controlled by
        the Master. This can be used to test a certain scenario or to solve a
        puzzle on the Diplomacy board, such as the Sherlock Holmes riddles published
        in the Diplomatic Pouch Zine. A PRIVACY password will be automatically
        assigned, because these are typically private games. After allowing the
        game to form, all powers will become dummies and the game starts immediately.
        The FORMING phase simply gets skipped. Make sure to have all relevant
        rules in place during preparation or when creating the game.

        The following rules are automatically included:
         - NO_DEADLINE
         - CD_DUMMIES
         - ALWAYS_WAIT

        To advance a turn the Master needs to push the Process Turn button
        or send a PROCESS command by e-mail. Use ROLLBACK and ROLLFORWARD to
        undo and redo phases, either by e-mail or from the corresponding
        Results page. Note that the Master CONTROLs all powers, and thus can
        give orders to each of them in a single message.

==================================================================
** START_MASTER ** ()
        This rule prevents the game from automatically starting once the last player
        joined. The Master will need to change the game status to active to begin the
        game.

==================================================================
** NO_PRESS ** (-PUBLIC_PRESS)
        Press is only allowed to and from the Master.  This rule is invalid
        when used with PUBLIC_PRESS or other rules that imply that any type
        of press is allowed.

==================================================================
** PUBLIC_PRESS ** (-NO_PRESS)
        Press is only allowed to and from the Master, and broadcast.
        (See the descriptions of the TOUCH_PRESS and REMOTE_PRESS rules for other
        implications of the PUBLIC_PRESS rule.)

==================================================================
** DONT_SKIP_PHASES ** ()
        If this rule is used, all phases (including phases where all players need
        to issue blank orders) will be played, and empty phases won't be skipped.

==================================================================
** IGNORE_ERRORS ** ()
        Order errors will be silently ignored.

==================================================================
** BUILD_ANY ** ()
        Powers may build new units at any owned supply center, not simply at
        their home supply centers.

==================================================================
** CIVIL_DISORDER ** (+CD_DUMMIES)
        Any power that has not submitted orders:

            - when the game's Master submits a PROCESS command, or

            - when the deadline has passed (or, if a grace period is
              specified in the TIMING line of the game's
              status file, after the expiration of
              the grace period),

        will have its orders entered automatically.  During movement phases, all
        units will HOLD, during retreat phases, all dislodged units will DISBAND,
        and during adjustment phases, all builds will be WAIVED, and all removals
        will be entered using random choice from among the power's on-board units,
        with preference given to retaining units that are situated on supply centers.

        Note also that unless the LATE_CHANGES rule is specified, the CIVIL_DISORDER
        rule also enforces the NO_LATE_CHANGES rule (described below).  This is to
        prevent players from changing their orders after the deadline to take advantage
        of powers that seem likely to go into civil disorder when a grace period expires.

        Individual powers may also be put into perpetual automatic, don't-even-wait-for-the-deadline,
        civil disorder (assuming no one like the Master enters orders for them)
        by setting the PLAYER information to DUMMY, and using the
        CD_DUMMIES rule, described below.

==================================================================
** CD_DUMMIES ** ()
        Assuming no powers have set their WAIT flag, orders will be
        processed as <i><u>soon</u></i> as all NON-DUMMY
        players have submitted orders.  Any powers having a PLAYER marked
        as a DUMMY will be considered in civil disorder (as described
        above) at that time.  Note the distinction -- CIVIL_DISORDER
        will default the orders of all powers (whether dummy or not), while
        CD_DUMMIES will default the orders only of the dummy powers.

==================================================================
** NO_DEADLINE ** ()
        In certain cases, e.g. for testing and solving Diplomacy puzzles (solitaire games),
        there's no need for a deadline, and thus also not for a Timing line. It's up to the
        GM to process each turn after all (relevant) orders are submitted, or for all players
        to submit their orders without setting their WAIT flag. This behavior can be
        influenced with the NO_WAIT and ALWAYS_WAIT options.

==================================================================
** REAL_TIME ** (!ALWAYS_WAIT)
        If this rule is used, the game will be processed AS SOON AS
        the last player submits orders (this player will have no opportunity
        to modify them).  Additionally, players will not be allowed to direct
        that the game wait for any deadline before processing.  This rule is
        used especially for games with very short deadlines (for example,
        10 minutes).

==================================================================
** ALWAYS_WAIT ** (!REAL_TIME)
        If this rule is used, orders will never process until the deadline
        has arrived (unless requested by the Master using a PROCESS
        command sent via e-mail).  This rule is incompatible with
        REAL_TIME and restricted to movement phases if NO_MINOR_WAIT is selected.

==================================================================
** PROPOSE_DIAS ** (!NO_DIAS)
        In games that use this rule, a player makes a proposal to conclude the
        game with a certain result, and all other players vote on it.
        The proposal may be a concession to a specific power or a draw including
        all survivors.  Any negative vote on the proposal will cause it to fail.

        In games NOT using this rule, draw and concession votes are never
        called for.  Instead, each player can select a single game ending
        (concession to his own power or to any other single power, or agreement to a
        draw that includes all surviving powers), and if ever all votes allow,
        the game will end.  No player's vote is revealed to any other player.  Note
        that if all players are ever found to be simultaneously voting for any
        result that is NOT a concession to their own power, the game will
        end in a draw shared among all surviving powers.

==================================================================
** NO_DIAS ** (!PROPOSE_DIAS)
        Games with this rule operate in their voting as do normal
        (non-PROPOSE_DIAS) games; that is, no proposal is ever made or
        vetoed.  However, games using the NO_DIAS rule may end in a
        result other than concession to a single player or agreement to a draw
        that includes all survivors.  If this rule is used, each player may vote
        either for the maximum size of a draw that he will accept which must
        include his power, or for a solo victory by his power, or for
        ANY result that does NOT include his power. Note that if all
        players are ever found to be voting for a result that does
        NOT include their own power, a draw shared among all surviving
        powers will be declared.

==================================================================
** HOLD_WIN ** ()
        To win a game using this rule, a player must achieve the winning condition
        two game-years in a row.

==================================================================
** SHARED_VICTORY ** ()
        When this rule is in effect, the game ends immediately after the first
        player reaches the victory condition. If any other player fulfills this
        condition at the same time (in games where this number is lower than
        the default of half of the number of SCs plus one), they are jointly
        declared winners (or participants in a draw, depending on definitions),
        irrespective of the fact that one may have a higher total than the
        other. This replaces the normal victory criterion where only a
        single player can be victorious and ties result in the continuation
        of the game.

==================================================================
*******************************************************
** VARIANT standard **
*******************************************************

** NO_CHECK ** ()
        This rule emulates face-to-face play, in which players could (by
        accident or design) issue invalid orders to their units.  This rule
        is also useful in NO_PRESS games to allow for limited player
        communication (see SIGNAL_SUPPORT for a more controlled alternative).

        When they are entered, movement phase orders are only very minimally
        checked for validity.  The ONLY checks that are made at the time an
        order is entered are:

            - Every component of the order must be understood.  That is, the
              order must appear to be a Diplomacy move, convoy, support or
              hold order, and all placenames must be identifiable on the map
              in use. This check catches inadvertant misspellings, such as "URK" for "UKR".
              In fact, this is known as the "Urk check."

            - Any placename abbreviation that is potentially ambiguous is declared
              erroneous and must be changed.  For example, the order "TYR H" is rejected
              because it may be an order for an army in Tyrolia to hold, or for a
              fleet in the Tyrrhenian Sea to hold.

            - A support for a fleet move may not specify the destination coast of
              the fleet.  This error must also be corrected.

        Therefore, most errors (including the omission of the fleet-path of
        a convoying army from its order!) are not detected until the phase
        is ready to process, at which time the erroneous orders will be ignored.
        All units that had been given erroneous or multiple orders will
        HOLD (and may receive support), and all erroneous orders will
        be reported in the results, flagged as (*invalid*).

==================================================================

<!-- RULE GROUP 0 Game Start -->
<!-- RULE POWER_CHOICE -->
<!-- RULE MULTIPLE_POWERS_PER_PLAYER -->
<!-- RULE NO_OBSERVATIONS -->
<!-- RULE SOLITAIRE +NO_DEADLINE +CD_DUMMIES +ALWAYS_WAIT -->
<!-- RULE START_MASTER -->
<!-- RULE GROUP 2 Player Press -->
<!-- RULE NO_PRESS -PUBLIC_PRESS -->
<!-- RULE PUBLIC_PRESS -NO_PRESS -->
<!-- RULE GROUP 3 Movement Order -->
<!-- RULE DONT_SKIP_PHASES -->
<!-- RULE IGNORE_ERRORS -->
<!-- RULE GROUP 5 Retreat and Adjustment Order -->
<!-- RULE BUILD_ANY -->
<!-- RULE GROUP 7 Late and Vacant Power Handling -->
<!-- RULE CIVIL_DISORDER +CD_DUMMIES -->
<!-- RULE CD_DUMMIES -->
<!-- RULE GROUP 9 Deadline Handling and Phase Processing -->
<!-- RULE NO_DEADLINE -->
<!-- RULE REAL_TIME !ALWAYS_WAIT -->
<!-- RULE ALWAYS_WAIT !REAL_TIME -->
<!-- RULE GROUP 10 Game Conclusion -->
<!-- RULE PROPOSE_DIAS !NO_DIAS -->
<!-- RULE NO_DIAS !PROPOSE_DIAS -->
<!-- RULE HOLD_WIN -->
<!-- RULE SHARED_VICTORY -->
<!-- RULE VARIANT standard -->
<!-- RULE GROUP 3 Movement Order -->
<!-- RULE NO_CHECK -->
<!-- RULE DIFFERENT_ADJUDICATION -->
