# AHU01 on a SpaceLogic MP-C-36A: terminals

| Terminal | Point | Kind | Range |
|---|---|---|---|
| Uc 1 | TF01_Ctrl | AO 0-10 V | 0 ... 100 % |
| Uc 2 | PF01_Ctrl | AO 0-10 V | 0 ... 100 % |
| Uc 3 | SC3_Ctrl | AO 0-10 V | 0 ... 100 % |
| Uc 4 | TV1_Ctrl | AO 0-10 V | 0 ... 100 % |
| Uc 5 | TV2_Ctrl | AO 0-10 V | 0 ... 100 % |
| DO 1 | FZ01_Cmd | DO relay |  |
| DO 2 | FZ02_Cmd | DO relay |  |
| DO 3 | TF01_Cmd | DO relay |  |
| DO 4 | PF01_Cmd | DO relay |  |
| DO 5 | SC3_Cmd | DO relay |  |
| DO 6 | P1_Cmd | DO relay |  |
| Ub 1 | TE1 | temperature sensor | 0 ... 100 |
| Ub 2 | TE2 | temperature sensor | -50 ... 100 |
| Ub 3 | TE3 | temperature sensor | -50 ... 50 |
| Ub 4 | TE4 | temperature sensor | -50 ... 80 |
| Ub 5 | TE5 | temperature sensor | -50 ... 80 |
| Ub 6 | TE6 | temperature sensor | -50 ... 50 |
| Ub 7 | TE7 | temperature sensor | -50 ... 100 |
| Ub 8 | TE8 | temperature sensor | -50 ... 50 |
| Ub 9 | PE1 | AI 0-10 V | 0 ... 500 Pa |
| Ub 10 | PE2 | AI 0-10 V | 0 ... 500 Pa |
| Ub 11 | PDE1 | AI 0-10 V | 0 ... 500 Pa |
| Ub 12 | PDE2 | AI 0-10 V | 0 ... 500 Pa |
| Ub 13 | PDE3 | AI 0-10 V | 0 ... 500 Pa |
| Ub 14 | PDE4 | AI 0-10 V | 0 ... 500 Pa |
| Ub 15 | PDE10 | AI 0-10 V | 0 ... 2000 Pa |
| Ub 16 | PDE20 | AI 0-10 V | 0 ... 2000 Pa |
| Ub 17 | FA01 | DI contact |  |
| Ub 18 | SB01 | DI contact |  |
| Ub 19 | HS10 | DI contact |  |
| Ub 20 | P1_Fdb | DI contact |  |
| Uc 6 | TF01_Fdb | DI contact |  |
| Uc 7 | PF01_Fdb | DI contact |  |
| Uc 8 | SC3_Fault | DI contact |  |
| network | TE00 | BACnet value AV | written by the server or another controller |
| network | TE10_1 | BACnet value AV | written by the server or another controller |
| network | TE10_2 | BACnet value AV | written by the server or another controller |
| network | TE10_3 | BACnet value AV | written by the server or another controller |
| network | Reset_DI | BACnet value BV | written by the server or another controller |

Soft inputs of the program (schedules, mode selectors, heat supply alarms) are not wired: bind them to
schedule objects, values or other controllers on the site.
