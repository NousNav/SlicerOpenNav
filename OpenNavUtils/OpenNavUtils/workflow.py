import weakref


class Step:
    """Contains actions required to enter/exit a single step in the workflow.

    See help(Workflow) for more information.
    """

    def __init__(self, names, setups, teardowns, validates):
        self.names = names
        self.setups = setups
        self.teardowns = teardowns
        self.validates = validates
        self.nextStep = None
        self.prevStep = None

    def __str__(self) -> str:
        return "step({})".format(",".join(self.names))

    @classmethod
    def one(cls, name, setup, teardown, validate):
        return Step((name,), (setup,), (teardown,), (validate,))

    def concat(self, other):
        cls = type(self)
        return cls(
            self.names + other.names,
            self.setups + other.setups,
            self.teardowns + other.teardowns,
            self.validates + other.validates,
        )

    @staticmethod
    def common_prefix_len(src_seq, dst_seq):
        """Find the length of the common prefix of two iterables.

        If there is no common prefix, or one of the two iterables is empty, then return 0.
        """
        count = 0
        for src_elem, dst_elem in zip(src_seq, dst_seq, strict=False):
            if src_elem != dst_elem:
                break
            count += 1
        return count

    @classmethod
    def transition(cls, src, dst):
        """Find the actions needed to transition from src (source) to dst (destination).

        Teardown src, then setup dst.
        """

        if not src or not dst:
            if src:
                yield from reversed(src.teardowns)
            if dst:
                yield from dst.setups
            return

        common_count = cls.common_prefix_len(src.names, dst.names)
        unique_teardowns = src.teardowns[common_count:]
        unique_setups = dst.setups[common_count:]

        yield from reversed(unique_teardowns)  # teardown in reverse order; context is a stack.
        yield from unique_setups

    @classmethod
    def validate(cls, dst):
        yield from dst.validates


class Workflow:
    """
    Each `Workflow` object has several optional attributes: `widget`, `setup`, `teardown`, `nested`. When the user leaves
    a stage in the workflow, invoke `teardown()`. When the user enters a stage in the workflow, make `widget` current and
    invoke `setup()`. These hooks allow the workflow definition to specify all "phases" of the workflow in one place.
    Navigating _within_ the `nested` workflows should not invoke setup or teardown of the parent.

    The recursive workflow structure is flattened into a linear sequence of Step objects. For example:

      [
        Step(('nn', 'patients'),
             (None, patients.enter),   # setup steps
             (None, patients.exit)),   # teardown steps
        Step(('nn', 'planning',     'skin'),
             (None, planning.enter, planning.planningStep1),
             (None, planning.exit,  None)),
        Step(('nn', 'planning',     'target'),
             (None, planning.enter, planning.planningStep2),
             (None, planning.exit,  None)),
        Step(('nn', 'planning',     'trajectory'),
             (None, planning.enter, planning.planningStep3),
             (None, planning.exit,  None)),
        Step(('nn', 'planning',     'landmarks'),
             (None, planning.enter, planning.planningStep4),
             (None, planning.exit,  None)),
      ]

    The linear sequence provides a clear definition of "previous" and "next" steps to be used in the bottom navigation
    bar.

    When navigating from `('nn', 'planning', 'target')` to `('nn', 'planning', 'landmarks')`, the common prefix
    `('nn', 'planning')` is removed and only the target teardown is invoked, and the landmarks setup are invoked
    (if present). enter/exit of the planning widget is unnecessary.

    When navigating from `('nn', 'planning', 'target')` to `('nn', 'patients')`, the common prefix `('nn',)` is removed.
    Then _both_ the target and planning teardowns are invoked, and the patients setup is invoked.

    `Step.transition` yields the sequence of setup/teardown functions that should be invoked, and `HomeLogic.goto`
     actually performs the navigation between steps.

    See https://github.com/OpenNav/OpenNav/pull/180 for more information.
    """

    def __init__(
        self,
        name,
        widget=None,
        setup=None,
        teardown=None,
        nested=(),
        engine=None,
        validate=None,
    ):
        self.name = name
        self.widget = widget
        self.setup = setup
        self.teardown = teardown
        self.nested = nested
        self.engine = weakref.ref(engine) if engine else None
        self.validate = validate

    def __del__(self):
        print(f"Deleting {self} ({self.name})")

    def gotoNext(self):
        if self.engine:
            self.engine().gotoNext()

    def gotoPrev(self):
        if self.engine:
            self.engine().gotoPrev()

    def gotoByName(self, name):
        if self.engine:
            self.engine().gotoByName(name)

    def flatten(self, stack):  # noqa: C901
        if self.widget:
            stack.addWidget(self.widget)

        if not self.nested:

            def setup():
                if self.widget:
                    stack.setCurrentWidget(self.widget)
                if self.setup:
                    self.setup()

            def teardown():
                if self.teardown:
                    self.teardown()

            def validate():
                if self.validate:
                    return self.validate()
                else:
                    return None

            yield Step.one(self.name, setup, teardown, validate)
        else:
            for nested in self.nested:

                def setup(idx=None):
                    if self.widget:
                        stack.setCurrentWidget(self.widget)
                    if self.setup:
                        self.setup()

                def teardown():
                    if self.teardown:
                        self.teardown()

                def validate():
                    if self.validate:
                        return self.validate()
                    else:
                        return None

                nested.engine = self.engine if isinstance(self.engine, (weakref.ReferenceType, type(None))) else weakref.ref(self.engine)

                this = Step.one(self.name, setup, teardown, validate)

                for step in nested.flatten(stack):
                    yield this.concat(step)
