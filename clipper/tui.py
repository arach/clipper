"""Terminal UI for clipper"""

import math
import re
import threading
from pathlib import Path
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Center
from textual.widgets import (
    Header, Footer, Static, Button, ProgressBar,
    Input, Label, DataTable, RichLog, Select, Switch, TextArea
)
from textual.binding import Binding
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

# ASCII logo with ANSI colors (green scissors)
LOGO_ASCII = """\
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;13;45;22m.\x1b[0m\x1b[38;2;11;47;21m.\x1b[0m\x1b[38;2;0;11;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;11;0m \x1b[0m\x1b[38;2;10;42;18m.\x1b[0m\x1b[38;2;7;36;14m \x1b[0m\x1b[38;2;0;11;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;26;79;43m.\x1b[0m\x1b[38;2;35;128;67m;\x1b[0m\x1b[38;2;21;82;41m.\x1b[0m\x1b[38;2;0;11;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;19;70;35m.\x1b[0m\x1b[38;2;28;110;57m,\x1b[0m\x1b[38;2;15;61;29m.\x1b[0m\x1b[38;2;0;10;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;25;76;41m.\x1b[0m\x1b[38;2;34;127;67m;\x1b[0m\x1b[38;2;33;125;66m;\x1b[0m\x1b[38;2;26;97;50m'\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;26;90;47m'\x1b[0m\x1b[38;2;23;101;51m'\x1b[0m\x1b[38;2;30;118;62m,\x1b[0m\x1b[38;2;14;62;29m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;12;42;19m.\x1b[0m\x1b[38;2;42;142;78m:\x1b[0m\x1b[38;2;33;123;64m;\x1b[0m\x1b[38;2;31;120;63m,\x1b[0m\x1b[38;2;23;91;46m'\x1b[0m\x1b[38;2;28;92;50m'\x1b[0m\x1b[38;2;25;104;54m'\x1b[0m\x1b[38;2;28;113;59m,\x1b[0m\x1b[38;2;33;124;65m;\x1b[0m\x1b[38;2;11;49;22m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;44;139;78m:\x1b[0m\x1b[38;2;32;122;64m;\x1b[0m\x1b[38;2;29;114;59m,\x1b[0m\x1b[38;2;25;106;54m,\x1b[0m\x1b[38;2;30;102;55m'\x1b[0m\x1b[38;2;31;118;62m,\x1b[0m\x1b[38;2;28;112;58m,\x1b[0m\x1b[38;2;33;125;65m;\x1b[0m\x1b[38;2;34;125;66m;\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;30;93;51m'\x1b[0m\x1b[38;2;32;121;63m;\x1b[0m\x1b[38;2;26;109;56m,\x1b[0m\x1b[38;2;22;94;48m'\x1b[0m\x1b[38;2;42;138;77m:\x1b[0m\x1b[38;2;29;114;59m,\x1b[0m\x1b[38;2;33;124;65m;\x1b[0m\x1b[38;2;37;134;71m;\x1b[0m\x1b[38;2;27;104;54m'\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;43;138;77m:\x1b[0m\x1b[38;2;33;122;64m;\x1b[0m\x1b[38;2;42;135;76m:\x1b[0m\x1b[38;2;32;121;63m;\x1b[0m\x1b[38;2;35;129;68m;\x1b[0m\x1b[38;2;37;133;70m;\x1b[0m\x1b[38;2;41;143;76m:\x1b[0m\x1b[38;2;13;53;24m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;24;73;40m.\x1b[0m\x1b[38;2;33;112;62m,\x1b[0m\x1b[38;2;69;204;115md\x1b[0m\x1b[38;2;47;155;84mc\x1b[0m\x1b[38;2;50;164;89mc\x1b[0m\x1b[38;2;25;92;47m'\x1b[0m\x1b[38;2;10;50;22m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;68;188;110mo\x1b[0m\x1b[38;2;54;170;93ml\x1b[0m\x1b[38;2;30;117;61m,\x1b[0m\x1b[38;2;36;127;67m;\x1b[0m\x1b[38;2;70;208;115md\x1b[0m\x1b[38;2;9;38;16m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;11;40;18m.\x1b[0m\x1b[38;2;63;174;102ml\x1b[0m\x1b[38;2;89;253;144m0\x1b[0m\x1b[38;2;82;237;133mk\x1b[0m\x1b[38;2;67;204;113md\x1b[0m\x1b[38;2;71;213;118mx\x1b[0m\x1b[38;2;69;207;115md\x1b[0m\x1b[38;2;24;80;40m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;19;58;30m.\x1b[0m\x1b[38;2;42;118;67m;\x1b[0m\x1b[38;2;66;183;106mo\x1b[0m\x1b[38;2;89;248;143mO\x1b[0m\x1b[38;2;87;251;141mO\x1b[0m\x1b[38;2;84;243;136mO\x1b[0m\x1b[38;2;79;232;129mk\x1b[0m\x1b[38;2;65;195;108md\x1b[0m\x1b[38;2;40;127;68m;\x1b[0m\x1b[38;2;36;118;63m;\x1b[0m\x1b[38;2;46;154;83mc\x1b[0m\x1b[38;2;39;136;73m:\x1b[0m\x1b[38;2;21;83;42m.\x1b[0m\x1b[38;2;10;46;20m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;35;98;56m'\x1b[0m\x1b[38;2;61;167;98ml\x1b[0m\x1b[38;2;86;231;137mk\x1b[0m\x1b[38;2;93;255;149m0\x1b[0m\x1b[38;2;91;255;146m0\x1b[0m\x1b[38;2;88;253;142mO\x1b[0m\x1b[38;2;85;246;138mO\x1b[0m\x1b[38;2;81;236;132mk\x1b[0m\x1b[38;2;75;223;124mx\x1b[0m\x1b[38;2;37;117;62m,\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;51;149;84mc\x1b[0m\x1b[38;2;65;198;109md\x1b[0m\x1b[38;2;55;177;96ml\x1b[0m\x1b[38;2;47;158;85mc\x1b[0m\x1b[38;2;39;139;74m:\x1b[0m\x1b[38;2;31;120;63m,\x1b[0m\x1b[38;2;25;104;53m'\x1b[0m\x1b[38;2;17;81;40m.\x1b[0m\x1b[38;2;10;56;25m.\x1b[0m\x1b[38;2;5;35;13m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;53;143;84m:\x1b[0m\x1b[38;2;76;205;122mx\x1b[0m\x1b[38;2;60;169;98ml\x1b[0m\x1b[38;2;56;160;91mc\x1b[0m\x1b[38;2;63;180;102mo\x1b[0m\x1b[38;2;81;230;130mk\x1b[0m\x1b[38;2;88;252;142mO\x1b[0m\x1b[38;2;84;244;136mO\x1b[0m\x1b[38;2;78;231;129mk\x1b[0m\x1b[38;2;71;214;119mx\x1b[0m\x1b[38;2;40;129;69m;\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;56;161;92ml\x1b[0m\x1b[38;2;63;193;106mo\x1b[0m\x1b[38;2;54;173;94ml\x1b[0m\x1b[38;2;45;151;81mc\x1b[0m\x1b[38;2;35;130;68m;\x1b[0m\x1b[38;2;24;100;51m'\x1b[0m\x1b[38;2;14;66;32m.\x1b[0m\x1b[38;2;9;51;23m.\x1b[0m\x1b[38;2;7;48;21m.\x1b[0m\x1b[38;2;7;52;23m.\x1b[0m\x1b[38;2;6;47;20m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;77;205;123mx\x1b[0m\x1b[38;2;30;91;49m'\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;32;99;52m'\x1b[0m\x1b[38;2;76;225;125mk\x1b[0m\x1b[38;2;70;211;117mx\x1b[0m\x1b[38;2;58;183;100mo\x1b[0m\x1b[38;2;11;48;22m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;22;67;36m.\x1b[0m\x1b[38;2;70;210;117mx\x1b[0m\x1b[38;2;58;184;101mo\x1b[0m\x1b[38;2;47;156;84mc\x1b[0m\x1b[38;2;15;59;28m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;6;50;22m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;57;150;90mc\x1b[0m\x1b[38;2;38;113;63m,\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;39;114;63m,\x1b[0m\x1b[38;2;60;189;104mo\x1b[0m\x1b[38;2;39;135;71m:\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;67;193;111md\x1b[0m\x1b[38;2;62;193;106mo\x1b[0m\x1b[38;2;31;107;56m,\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;18;87;43m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;54;146;86mc\x1b[0m\x1b[38;2;32;98;52m'\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;44;126;72m;\x1b[0m\x1b[38;2;45;153;83mc\x1b[0m\x1b[38;2;13;57;26m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;28;84;45m.\x1b[0m\x1b[38;2;67;204;113md\x1b[0m\x1b[38;2;43;141;76m:\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;14;55;25m.\x1b[0m\x1b[38;2;36;128;69m;\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;65;182;106mo\x1b[0m\x1b[38;2;21;69;35m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;8;32;13m \x1b[0m\x1b[38;2;40;117;66m;\x1b[0m\x1b[38;2;49;158;87mc\x1b[0m\x1b[38;2;14;62;30m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;31;98;52m'\x1b[0m\x1b[38;2;61;189;104mo\x1b[0m\x1b[38;2;35;118;63m;\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;29;88;49m'\x1b[0m\x1b[38;2;57;164;97ml\x1b[0m\x1b[38;2;6;37;15m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;34;104;56m,\x1b[0m\x1b[38;2;44;134;72m:\x1b[0m\x1b[38;2;42;131;70m;\x1b[0m\x1b[38;2;45;139;75m:\x1b[0m\x1b[38;2;48;148;80m:\x1b[0m\x1b[38;2;46;143;78m:\x1b[0m\x1b[38;2;21;79;40m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;7;33;12m \x1b[0m\x1b[38;2;26;89;45m'\x1b[0m\x1b[38;2;34;116;61m,\x1b[0m\x1b[38;2;29;104;54m,\x1b[0m\x1b[38;2;23;87;44m.\x1b[0m\x1b[38;2;25;91;46m'\x1b[0m\x1b[38;2;34;112;60m,\x1b[0m\x1b[38;2;23;78;41m.\x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m\x1b[38;2;0;12;0m \x1b[0m
"""

from .compress import (
    probe_video, compress, VideoInfo,
    PRESETS, DEFAULT_PRESET, Preset,
    detect_preset_from_filename,
)
from .watcher import Watcher, WatchFolders, Job, JobStatus
from .config import get_config, get_config_path, reload_config


class VideoInfoPanel(Static):
    """Display video metadata"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._info: VideoInfo | None = None
        self._preset: Preset | None = None

    def update_info(self, info: VideoInfo | None, preset: Preset | None = None):
        self._info = info
        self._preset = preset
        self.refresh()

    def render(self):
        if not self._info:
            return Panel(
                "[dim]No video loaded[/dim]\n\nPaste path below or drop into inbox",
                title="[bold cyan][ INPUT ][/bold cyan]",
                border_style="cyan",
            )

        i = self._info
        preset_str = f"[magenta]{self._preset.name}[/magenta]" if self._preset else "[dim]auto[/dim]"
        content = f"""[bold white]{i.path.name}[/bold white]

[cyan]Dimensions[/cyan]  {i.dimensions}
[cyan]Duration[/cyan]    {i.duration:.1f}s
[cyan]Codec[/cyan]       {i.codec}
[cyan]FPS[/cyan]         {i.fps:.0f}
[cyan]Bitrate[/cyan]     {i.bitrate // 1000} kbps
[cyan]Size[/cyan]        [bold yellow]{i.size_mb:.1f} MB[/bold yellow]
[cyan]Preset[/cyan]      {preset_str}"""

        return Panel(
            content,
            title="[bold cyan][ INPUT ][/bold cyan]",
            border_style="cyan",
        )


class OutputPanel(Static):
    """Display compression results"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._result = None

    def set_result(self, original_mb: float, compressed_mb: float, reduction: float, path: Path, preset_name: str = ""):
        self._result = (original_mb, compressed_mb, reduction, path, preset_name)
        self.refresh()

    def clear(self):
        self._result = None
        self.refresh()

    def render(self):
        if not self._result:
            return Panel(
                "[dim]Waiting for compression...[/dim]",
                title="[bold green][ OUTPUT ][/bold green]",
                border_style="green",
            )

        orig, comp, reduction, path, preset_name = self._result
        content = f"""[bold white]{path.name}[/bold white]

[green]Original[/green]    {orig:.1f} MB
[green]Compressed[/green]  [bold]{comp:.1f} MB[/bold]
[green]Reduction[/green]   [bold yellow]{reduction:.1f}%[/bold yellow]
[green]Preset[/green]      [magenta]{preset_name}[/magenta]"""

        return Panel(
            content,
            title="[bold green][ OUTPUT ][/bold green]",
            border_style="green",
        )


class QueuePanel(Static):
    """Display job queue from watcher"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._jobs: list[Job] = []
        self._watch_path: Path | None = None

    def set_watch_path(self, path: Path):
        self._watch_path = path
        self.refresh()

    def update_jobs(self, jobs: list[Job]):
        self._jobs = jobs
        self.refresh()

    def render(self):
        if not self._watch_path:
            content = "[dim]Watcher not started[/dim]"
        elif not self._jobs:
            content = f"[dim]Watching:[/dim] {self._watch_path}/inbox\n\n[dim]No jobs in queue[/dim]\n\n[dim italic]Drop files with preset suffix:[/dim]\n  video[magenta]-social[/magenta].mp4\n  video[magenta]-web[/magenta].mp4\n  video[magenta]-archive[/magenta].mp4\n  video[magenta]-tiny[/magenta].mp4"
        else:
            lines = [f"[dim]Watching:[/dim] {self._watch_path}/inbox\n"]
            for job in self._jobs[-8:]:  # Show last 8 jobs
                status_icon = {
                    JobStatus.QUEUED: "[yellow]>[/yellow]",
                    JobStatus.PROCESSING: "[cyan]~[/cyan]",
                    JobStatus.DONE: "[green]+[/green]",
                    JobStatus.FAILED: "[red]![/red]",
                }[job.status]

                name = job.input_path.name[:30]
                if len(job.input_path.name) > 30:
                    name = name[:27] + "..."

                if job.status == JobStatus.PROCESSING:
                    pct = f"[cyan]{job.progress*100:3.0f}%[/cyan]"
                    lines.append(f"{status_icon} {name} {pct}")
                elif job.status == JobStatus.DONE and job.result:
                    reduction = f"[green]-{job.result.reduction_percent:.0f}%[/green]"
                    lines.append(f"{status_icon} {name} {reduction}")
                else:
                    lines.append(f"{status_icon} {name}")

            content = "\n".join(lines)

        return Panel(
            content,
            title="[bold magenta][ QUEUE ][/bold magenta]",
            border_style="magenta",
        )


class StatusLog(RichLog):
    """Styled log widget with markup enabled"""

    def __init__(self, **kwargs):
        super().__init__(markup=True, **kwargs)


def _get_onboarded_path() -> Path:
    """Get path to onboarding marker file"""
    return Path.home() / ".config" / "clipper" / ".onboarded"


def has_been_onboarded() -> bool:
    """Check if user has seen the onboarding screen"""
    return _get_onboarded_path().exists()


def mark_onboarded():
    """Mark that user has completed onboarding"""
    path = _get_onboarded_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def shimmer_logo(logo: str, frame: int) -> Text:
    """Apply a shimmer effect - a diagonal wave that sweeps across once"""
    result = Text()
    lines = logo.split('\n')

    # Wave position moves diagonally across the logo
    wave_pos = frame * 1.5  # Speed of the wave

    for y, line in enumerate(lines):
        pos = 0
        x = 0  # Track visual character position
        pattern = re.compile(r'\x1b\[38;2;(\d+);(\d+);(\d+)m(.)\x1b\[0m')

        for match in pattern.finditer(line):
            if match.start() > pos:
                result.append(line[pos:match.start()])

            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            char = match.group(4)

            # Diagonal wave: position based on x + y
            char_pos = x + y * 0.5

            # Calculate shimmer intensity based on distance from wave
            distance = abs(char_pos - wave_pos)
            brightness = max(0, 1.0 - distance * 0.12)  # Soft glow falloff

            # Brighten the color
            r = min(255, int(r + (255 - r) * brightness * 0.7))
            g = min(255, int(g + (255 - g) * brightness * 0.7))
            b = min(255, int(b + (255 - b) * brightness * 0.7))

            result.append(char, style=f"rgb({r},{g},{b})")
            pos = match.end()
            x += 1

        if pos < len(line):
            result.append(line[pos:])

        if y < len(lines) - 1:
            result.append('\n')

    return result


class AboutScreen(Screen):
    """About/onboarding screen with logo and quick start guide"""

    CSS = """
    AboutScreen {
        align: center middle;
        background: $surface;
    }

    #about-container {
        width: 80;
        height: auto;
        padding: 1 2;
        background: $surface;
    }

    #top-row {
        height: auto;
        width: 100%;
    }

    #logo-column {
        width: 34;
        height: auto;
        padding-right: 1;
        border-right: tall $primary-darken-2;
    }

    #logo-display {
        width: auto;
        height: auto;
    }

    #info-column {
        width: 1fr;
        height: 100%;
        padding-left: 2;
    }

    #version-text {
        text-align: left;
    }

    #tagline {
        color: $text-muted;
    }

    #quickstart {
        margin-top: 1;
    }

    #info-spacer {
        height: 1fr;
    }

    #info-footer {
        height: auto;
        color: $text-muted;
    }

    /* Responsive classes applied programmatically */
    .narrow #logo-column {
        display: none;
    }

    .narrow #info-column {
        padding-left: 0;
    }

    .wide #about-container {
        width: 90;
        padding: 2 3;
    }

    .wide #logo-column {
        width: 38;
        padding: 1;
    }

    .extra-wide #about-container {
        width: 110;
        padding: 3 4;
    }

    .extra-wide #logo-column {
        width: 42;
        padding: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("enter", "dismiss", "Close", show=False),
        Binding("space", "dismiss", "Close", show=False),
    ]

    def __init__(self, is_onboarding: bool = False):
        super().__init__()
        self.is_onboarding = is_onboarding
        self._shimmer_frame = 0
        self._shimmer_timer = None

    def compose(self) -> ComposeResult:
        with Vertical(id="about-container"):
            with Horizontal(id="top-row"):
                # Left column: Logo
                with Vertical(id="logo-column"):
                    yield Static(Text.from_ansi(LOGO_ASCII), id="logo-display")

                # Right column: Info + Quick Start + Footer
                with Vertical(id="info-column"):
                    yield Static("[bold green]clipper[/bold green] v0.1.0", id="version-text", markup=True)
                    yield Static("Video compression TUI", id="tagline")
                    yield Static("Drop, compress, share.", id="tagline2")

                    quickstart = """
[bold cyan]Quick Start[/bold cyan]
  [yellow]w[/yellow]  Start watcher
  [yellow]c[/yellow]  Compress video
  [yellow]s[/yellow]  Share to clipboard
  [yellow]e[/yellow]  Edit config

[bold cyan]Presets[/bold cyan] (filename suffix)
  [magenta]-social[/magenta]  50%, CRF 28
  [magenta]-web[/magenta]     75%, CRF 23
  [magenta]-archive[/magenta] 100%, CRF 18
  [magenta]-tiny[/magenta]    25%, CRF 32"""
                    yield Static(quickstart, id="quickstart", markup=True)

                    # Spacer pushes footer to bottom
                    yield Static("", id="info-spacer")

                    # Footer at bottom
                    if self.is_onboarding:
                        yield Static("made with [red]♥[/red] by [cyan]@arach[/cyan]\n[bold]Press any key to get started[/bold]", id="info-footer", markup=True)
                    else:
                        yield Static("made with [red]♥[/red] by [cyan]@arach[/cyan]\n[dim]Press any key to continue[/dim]", id="info-footer", markup=True)

    def on_mount(self):
        """Start shimmer animation"""
        self._shimmer_timer = self.set_interval(1/15, self._update_shimmer)
        self._update_responsive()

    def _schedule_next_shimmer(self):
        """Schedule another shimmer in 2 minutes"""
        self.set_timer(120, self._restart_shimmer)

    def _restart_shimmer(self):
        """Restart the shimmer animation"""
        self._shimmer_frame = 0
        self._shimmer_timer = self.set_interval(1/15, self._update_shimmer)

    def on_resize(self, event):
        """Update responsive classes on resize"""
        self._update_responsive()

    def _update_responsive(self):
        """Apply responsive CSS classes based on terminal width"""
        width = self.app.size.width
        container = self.query_one("#about-container")

        # Remove all responsive classes
        container.remove_class("narrow", "wide", "extra-wide")

        # Apply appropriate class
        if width < 70:
            container.add_class("narrow")
        elif width > 130:
            container.add_class("extra-wide")
        elif width > 100:
            container.add_class("wide")

    def _update_shimmer(self):
        """Update shimmer animation frame"""
        self._shimmer_frame += 1

        # Stop after wave passes through (~35 frames for full diagonal sweep)
        if self._shimmer_frame > 35:
            if self._shimmer_timer:
                self._shimmer_timer.stop()
                self._shimmer_timer = None
            # Set final static logo
            try:
                logo_display = self.query_one("#logo-display", Static)
                logo_display.update(Text.from_ansi(LOGO_ASCII))
            except Exception:
                pass
            # Schedule next shimmer in 2 minutes
            self._schedule_next_shimmer()
            return

        try:
            logo_display = self.query_one("#logo-display", Static)
            logo_display.update(shimmer_logo(LOGO_ASCII, self._shimmer_frame))
        except Exception:
            pass  # Screen might be closing

    def action_dismiss(self):
        if self._shimmer_timer:
            self._shimmer_timer.stop()
        if self.is_onboarding:
            mark_onboarded()
        self.app.pop_screen()

    def on_key(self, event):
        if self._shimmer_timer:
            self._shimmer_timer.stop()
        if self.is_onboarding:
            mark_onboarded()
        self.app.pop_screen()


class ConfigScreen(Screen):
    """Configuration editor screen with simple/advanced modes"""

    CSS = """
    ConfigScreen {
        align: center middle;
    }

    #config-container {
        width: 80%;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #config-header {
        height: 3;
        margin-bottom: 1;
    }

    #config-title {
        width: 1fr;
        text-style: bold;
        color: $text;
        padding: 0 1;
    }

    #mode-toggle {
        width: auto;
    }

    .config-row {
        height: 3;
        margin: 1 0;
    }

    .config-label {
        width: 20;
        padding: 0 1;
    }

    .config-input {
        width: 1fr;
    }

    #simple-mode {
        height: auto;
    }

    #advanced-mode {
        display: none;
        height: auto;
    }

    #advanced-mode.active {
        display: block;
    }

    #simple-mode.hidden {
        display: none;
    }

    #config-editor {
        height: 20;
        margin: 1 0;
    }

    #config-buttons {
        height: 3;
        margin-top: 2;
        align: center middle;
    }

    #config-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
        Binding("tab", "toggle_mode", "Toggle Mode", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.advanced_mode = False

    def compose(self) -> ComposeResult:
        config = get_config()
        config_path = get_config_path()
        raw_content = config_path.read_text() if config_path.exists() else ""

        with Container(id="config-container"):
            with Horizontal(id="config-header"):
                yield Static("[bold cyan][ CONFIGURATION ][/bold cyan]", id="config-title")
                yield Button("Advanced", id="mode-toggle", variant="default")

            # Simple mode - form inputs
            with Container(id="simple-mode"):
                with Horizontal(classes="config-row"):
                    yield Static("Watch Folder:", classes="config-label")
                    yield Input(
                        str(config.folders.watch_base),
                        id="watch-base-input",
                        classes="config-input",
                    )

                with Horizontal(classes="config-row"):
                    yield Static("Default Preset:", classes="config-label")
                    yield Select(
                        [(name, name) for name in PRESETS.keys()],
                        value=config.presets.default,
                        id="default-preset-select",
                        classes="config-input",
                    )

                with Horizontal(classes="config-row"):
                    yield Static("Auto-start Watcher:", classes="config-label")
                    yield Switch(value=config.behavior.auto_start_watcher, id="auto-start-switch")

                with Horizontal(classes="config-row"):
                    yield Static("Delete Source:", classes="config-label")
                    yield Switch(value=config.behavior.delete_source, id="delete-source-switch")

                with Horizontal(classes="config-row"):
                    yield Static("Notifications:", classes="config-label")
                    yield Switch(value=config.behavior.notifications, id="notifications-switch")

            # Advanced mode - raw TOML editor
            with Container(id="advanced-mode"):
                yield Static(f"[dim]{config_path}[/dim]", id="config-path")
                yield TextArea(raw_content, language="toml", id="config-editor", show_line_numbers=True)

            with Horizontal(id="config-buttons"):
                yield Button("Save", id="save-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "mode-toggle":
            self.action_toggle_mode()

    def action_toggle_mode(self):
        """Toggle between simple and advanced mode"""
        self.advanced_mode = not self.advanced_mode

        simple = self.query_one("#simple-mode")
        advanced = self.query_one("#advanced-mode")
        toggle_btn = self.query_one("#mode-toggle", Button)

        if self.advanced_mode:
            simple.add_class("hidden")
            advanced.add_class("active")
            toggle_btn.label = "Simple"
            # Sync form values to raw TOML
            self._sync_form_to_editor()
        else:
            simple.remove_class("hidden")
            advanced.remove_class("active")
            toggle_btn.label = "Advanced"

    def _sync_form_to_editor(self):
        """Update raw editor with current form values"""
        watch_base = self.query_one("#watch-base-input", Input).value
        default_preset = self.query_one("#default-preset-select", Select).value
        auto_start = self.query_one("#auto-start-switch", Switch).value
        delete_source = self.query_one("#delete-source-switch", Switch).value
        notifications = self.query_one("#notifications-switch", Switch).value

        content = f'''# clipper configuration

[folders]
watch_base = "{watch_base}"

[presets]
default = "{default_preset}"

[behavior]
auto_start_watcher = {str(auto_start).lower()}
delete_source = {str(delete_source).lower()}
notifications = {str(notifications).lower()}
'''
        editor = self.query_one("#config-editor", TextArea)
        editor.load_text(content)

    def action_save(self):
        """Save config and return to main screen"""
        if self.advanced_mode:
            # Save raw TOML from editor
            editor = self.query_one("#config-editor", TextArea)
            config_content = editor.text
        else:
            # Build TOML from form
            watch_base = self.query_one("#watch-base-input", Input).value
            default_preset = self.query_one("#default-preset-select", Select).value
            auto_start = self.query_one("#auto-start-switch", Switch).value
            delete_source = self.query_one("#delete-source-switch", Switch).value
            notifications = self.query_one("#notifications-switch", Switch).value

            config_content = f'''# clipper configuration

[folders]
watch_base = "{watch_base}"

[presets]
default = "{default_preset}"

[behavior]
auto_start_watcher = {str(auto_start).lower()}
delete_source = {str(delete_source).lower()}
notifications = {str(notifications).lower()}
'''

        # Write to file
        config_path = get_config_path()
        config_path.write_text(config_content)

        # Reload config
        reload_config()

        self.app.pop_screen()
        self.app.notify("Config saved!", severity="information")

    def action_cancel(self):
        """Return to main screen without saving"""
        self.app.pop_screen()


class VidToolsApp(App):
    """Video compression TUI"""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        height: 100%;
        padding: 1;
    }

    #top-panels {
        height: auto;
        max-height: 14;
    }

    VideoInfoPanel, OutputPanel {
        width: 1fr;
        height: auto;
        min-height: 12;
        margin: 0 1;
    }

    #queue-row {
        height: auto;
        max-height: 14;
        margin: 0 1;
    }

    QueuePanel {
        width: 100%;
        height: auto;
        min-height: 10;
    }

    #input-row {
        height: 3;
        margin: 1;
        padding: 0 1;
    }

    #file-input {
        width: 2fr;
    }

    #preset-select {
        width: 1fr;
    }

    #progress-container {
        height: 3;
        margin: 1;
        padding: 0 1;
        display: none;
    }

    #progress-container.active {
        display: block;
    }

    ProgressBar {
        width: 100%;
    }

    #button-row {
        height: 3;
        margin: 1;
        padding: 0 1;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    #compress-btn {
        background: $success;
    }

    #watch-btn {
        background: $warning;
    }

    #log-container {
        height: 1fr;
        margin: 1;
        border: solid $primary;
    }

    StatusLog {
        height: 100%;
        background: $surface-darken-1;
    }
    """

    BINDINGS = [
        Binding("escape", "unfocus", "Unfocus", show=False),
        Binding("q", "quit", "Quit"),
        Binding("c", "compress", "Compress"),
        Binding("s", "share", "Share"),
        Binding("w", "toggle_watch", "Watch"),
        Binding("e", "open_config", "Config"),
        Binding("a", "about", "About"),
        Binding("l", "copy_log", "Copy Log"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
    ]

    def __init__(self):
        super().__init__()
        self.video_info: VideoInfo | None = None
        self.selected_preset: Preset = DEFAULT_PRESET
        self.watcher: Watcher | None = None
        self.watch_folders: WatchFolders | None = None
        self._last_escape: float = 0
        self._last_output: Path | None = None
        self._log_history: list[str] = []

    def write_log(self, message: str):
        """Write to log panel and keep history"""
        self._log_history.append(message)
        log_widget = self.query_one("#log", StatusLog)
        log_widget.write(message)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            with Horizontal(id="top-panels"):
                yield VideoInfoPanel(id="info-panel")
                yield OutputPanel(id="output-panel")

            with Container(id="queue-row"):
                yield QueuePanel(id="queue-panel")

            with Horizontal(id="input-row"):
                yield Input(placeholder="Enter video path...", id="file-input")
                yield Select(
                    [(f"{p.name} - {p.description[:30]}", p.name) for p in PRESETS.values()],
                    value="social",
                    id="preset-select",
                )
                yield Button("Load", id="load-btn", variant="primary")

            with Horizontal(id="progress-container"):
                yield ProgressBar(id="progress", show_eta=True)

            with Horizontal(id="button-row"):
                yield Button("Compress", id="compress-btn", variant="success", disabled=True)
                yield Button("Ready to share?", id="share-btn", variant="primary", disabled=True)
                yield Button("Start Watcher", id="watch-btn", variant="warning")

            with Container(id="log-container"):
                yield StatusLog(id="log", highlight=True)

        yield Footer()

    def on_mount(self):
        self.title = "clipper"
        self.sub_title = "video compression utility"
        # Start unfocused so keybindings are discoverable (defer to after render)
        self.call_later(self.set_focus, None)

        # Show onboarding splash for first-time users
        if not has_been_onboarded():
            self.call_later(self.push_screen, AboutScreen(is_onboarding=True))

        config = get_config()
        self.write_log("[bold cyan]clipper[/bold cyan] v0.1.0")
        self.write_log(f"[dim]Config: {get_config_path()}[/dim]")
        self.write_log(f"[dim]Watch folder: {config.folders.watch_base}[/dim]")
        self.write_log(f"[dim]Presets: {', '.join(PRESETS.keys())} | Press [bold]e[/bold] to edit config[/dim]")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "load-btn":
            self.action_load_video()
        elif event.button.id == "compress-btn":
            self.action_compress()
        elif event.button.id == "share-btn":
            self.action_share()
        elif event.button.id == "watch-btn":
            self.action_toggle_watch()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "file-input":
            self.action_load_video()

    def on_paste(self, event) -> None:
        """Handle drag & drop / paste of file paths"""
        text = event.text.strip()

        # Clean up the path (remove quotes, handle escapes)
        if text.startswith(("'", '"')) and text.endswith(("'", '"')):
            text = text[1:-1]
        text = text.replace("\\ ", " ")  # Handle escaped spaces

        # Check if it looks like a video file
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv'}
        path = Path(text)

        if path.suffix.lower() in video_extensions and path.exists():
            # Put path in input and load it
            file_input = self.query_one("#file-input", Input)
            file_input.value = str(path)
            self.action_load_video()
            event.prevent_default()
        # Otherwise let normal paste behavior happen

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "preset-select":
            self.selected_preset = PRESETS[event.value]
            if self.video_info:
                info_panel = self.query_one("#info-panel", VideoInfoPanel)
                info_panel.update_info(self.video_info, self.selected_preset)

    def action_load_video(self):
        file_input = self.query_one("#file-input", Input)
        path_str = file_input.value.strip()

        if not path_str:
            return

        path = Path(path_str).expanduser().resolve()

        if not path.exists():
            self.write_log(f"[red]Error:[/red] File not found: {path}")
            return

        self.write_log(f"[cyan]Probing:[/cyan] {path.name}...")
        load_btn = self.query_one("#load-btn", Button)
        load_btn.disabled = True
        load_btn.label = "Loading..."

        def do_probe():
            try:
                info = probe_video(path)

                def finish():
                    self.video_info = info

                    # Auto-detect preset from filename
                    detected = detect_preset_from_filename(path)
                    if detected:
                        self.selected_preset = detected
                        select = self.query_one("#preset-select", Select)
                        select.value = detected.name
                        self.write_log(f"[magenta]Preset detected:[/magenta] {detected.name}")

                    info_panel = self.query_one("#info-panel", VideoInfoPanel)
                    info_panel.update_info(self.video_info, self.selected_preset)

                    output_panel = self.query_one("#output-panel", OutputPanel)
                    output_panel.clear()

                    compress_btn = self.query_one("#compress-btn", Button)
                    compress_btn.disabled = False

                    self.write_log(f"[green]Loaded:[/green] {info.dimensions}, {info.size_mb:.1f} MB")
                    load_btn.disabled = False
                    load_btn.label = "Load"

                self.call_from_thread(finish)

            except Exception as e:
                def on_error():
                    self.write_log(f"[red]Error:[/red] {e}")
                    load_btn.disabled = False
                    load_btn.label = "Load"
                self.call_from_thread(on_error)

        thread = threading.Thread(target=do_probe, daemon=True)
        thread.start()

    def action_compress(self):
        if not self.video_info:
            return

        progress_container = self.query_one("#progress-container")
        progress = self.query_one("#progress", ProgressBar)
        compress_btn = self.query_one("#compress-btn", Button)

        compress_btn.disabled = True
        progress_container.add_class("active")
        progress.update(total=100, progress=0)

        preset = self.selected_preset
        self.write_log(f"[yellow]Compressing:[/yellow] {self.video_info.path.name}")
        self.write_log(f"[dim]  Preset: {preset.name} | Scale: {preset.scale*100:.0f}% | CRF: {preset.crf}[/dim]")

        def on_progress(p: float):
            self.call_from_thread(progress.update, progress=p * 100)

        def do_compress():
            try:
                result = compress(
                    self.video_info.path,
                    preset=preset,
                    on_progress=on_progress,
                )

                def finish():
                    progress.update(progress=100)
                    progress_container.remove_class("active")
                    output_panel = self.query_one("#output-panel", OutputPanel)
                    output_panel.set_result(
                        result.original_size / (1024 * 1024),
                        result.compressed_size / (1024 * 1024),
                        result.reduction_percent,
                        result.output_path,
                        preset.name,
                    )
                    self.write_log(f"[green]Done![/green] {result.output_path}")
                    self.write_log(f"[green]Reduced:[/green] {result.reduction_percent:.1f}%")
                    compress_btn.disabled = False
                    # Enable share button
                    self._last_output = result.output_path
                    share_btn = self.query_one("#share-btn", Button)
                    share_btn.disabled = False

                self.call_from_thread(finish)

            except Exception as e:
                def error():
                    progress_container.remove_class("active")
                    self.write_log(f"[red]Error:[/red] {e}")
                    compress_btn.disabled = False

                self.call_from_thread(error)

        thread = threading.Thread(target=do_compress, daemon=True)
        thread.start()

    def action_toggle_watch(self):
        watch_btn = self.query_one("#watch-btn", Button)
        queue_panel = self.query_one("#queue-panel", QueuePanel)

        if self.watcher and self.watcher.is_running:
            # Stop watcher
            self.watcher.stop()
            watch_btn.label = "Start Watcher"
            self.write_log("[yellow]Watcher stopped[/yellow]")
        else:
            # Start watcher
            config = get_config()
            watch_base = config.folders.watch_base
            self.watch_folders = WatchFolders.create(watch_base)
            queue_panel.set_watch_path(watch_base)

            def on_job_added(job: Job):
                def update():
                    queue_panel.update_jobs(self.watcher.jobs)
                    self.write_log(f"[cyan]Queued:[/cyan] {job.input_path.name} [{job.preset.name}]")
                self.call_from_thread(update)

            def on_job_updated(job: Job):
                def update():
                    queue_panel.update_jobs(self.watcher.jobs)
                self.call_from_thread(update)

            def on_job_done(job: Job):
                def update():
                    queue_panel.update_jobs(self.watcher.jobs)
                    if job.status == JobStatus.DONE and job.result:
                        self.write_log(f"[green]Completed:[/green] {job.result.output_path.name} (-{job.result.reduction_percent:.1f}%)")
                    elif job.status == JobStatus.FAILED:
                        self.write_log(f"[red]Failed:[/red] {job.input_path.name} - {job.error}")
                self.call_from_thread(update)

            self.watcher = Watcher(
                self.watch_folders,
                on_job_added=on_job_added,
                on_job_updated=on_job_updated,
                on_job_done=on_job_done,
            )
            self.watcher.start()

            watch_btn.label = "Stop Watcher"
            self.write_log(f"[green]Watcher started[/green]")
            self.write_log(f"[dim]Inbox: {self.watch_folders.inbox}[/dim]")
            self.write_log(f"[dim]Output: {self.watch_folders.done}[/dim]")

    def action_unfocus(self):
        """Return to command mode, double-tap to quit"""
        import time
        now = time.time()

        # If already unfocused and escape pressed twice within 0.5s, quit
        if self.focused is None and (now - self._last_escape) < 0.5:
            self.exit()
            return

        self._last_escape = now
        self.set_focus(None)

    def action_share(self):
        """Copy output path to clipboard"""
        if not self._last_output:
            self.notify("Nothing to share yet", severity="warning")
            return

        import subprocess
        path_str = str(self._last_output)

        # Copy to clipboard using pbcopy (macOS)
        subprocess.run(["pbcopy"], input=path_str.encode(), check=True)

        self.write_log(f"[cyan]Copied to clipboard:[/cyan] {self._last_output.name}")
        self.notify("Path copied! Ready to paste.", severity="information")

    def action_copy_log(self):
        """Copy log contents to clipboard"""
        import subprocess
        import re

        if not self._log_history:
            self.notify("No logs to copy", severity="warning")
            return

        plain_logs = []
        for line in self._log_history:
            # Remove Rich markup tags like [bold], [/bold], [red], [dim], etc.
            # Match [word] or [/word] or [word attr] patterns
            plain = re.sub(r'\[/?[\w\s]+\]', '', line)
            plain_logs.append(plain)

        text = '\n'.join(plain_logs)
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        self.notify(f"Copied {len(self._log_history)} log lines!", severity="information")

    def action_clear_log(self):
        log = self.query_one("#log", StatusLog)
        log.clear()
        self._log_history.clear()

    def action_open_config(self):
        """Open config editor screen"""
        self.push_screen(ConfigScreen())

    def action_about(self):
        """Show about screen with logo"""
        self.push_screen(AboutScreen())

    def on_unmount(self):
        if self.watcher:
            self.watcher.stop()


def main():
    app = VidToolsApp()
    app.run()


if __name__ == "__main__":
    main()
