#!/usr/bin/python3

# © 2024 Microchip Technology Inc. and its subsidiaries
# Subject to your compliance with these terms, you may use this Microchip software
# and any derivatives exclusively with Microchip products. You are responsible for 
# complying with third party license terms applicable to your use of third party 
# software (including open source software) that may accompany this Microchip 
# software.
# Redistribution of this Microchip software in source or binary form is allowed and
# must include the above terms of use and the following disclaimer with the 
# distribution and accompanying materials.
# SOFTWARE IS “AS IS.” NO WARRANTIES, WHETHER EXPRESS, IMPLIED OR STATUTORY, APPLY 
# TO THIS SOFTWARE, INCLUDING ANY IMPLIED WARRANTIES OF NON-INFRINGEMENT, 
# MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE. IN NO EVENT WILL MICROCHIP BE
# LIABLE FOR ANY INDIRECT, SPECIAL, PUNITIVE, INCIDENTAL OR CONSEQUENTIAL LOSS, 
# DAMAGE, COST OR EXPENSE OF ANY KIND WHATSOEVER RELATED TO THE SOFTWARE, HOWEVER 
# CAUSED, EVEN IF MICROCHIP HAS BEEN ADVISED OF THE POSSIBILITY OR THE DAMAGES ARE 
# FORESEEABLE. TO THE FULLEST EXTENT ALLOWED BY LAW, MICROCHIP’S TOTAL LIABILITY ON 
# ALL CLAIMS RELATED TO THE SOFTWARE WILL NOT EXCEED AMOUNT OF FEES, IF ANY, YOU 
# PAID DIRECTLY TO MICROCHIP FOR THIS SOFTWARE.

# @file     print_utils.py
#
# @brief    Various print function definitions
#
# @date     June 2, 2023
#
# @version  1.0.1
#
# @ref      http://www.linux-usb.org/usb.ids
#
# @brief    Displays a banner with upper and lower character bars with
#           the user message in between. Bar length is auto calculated
#           based on the banner_msg length. Each bar can be composed of
#           a single char or multiple characters i.e. '━' or '━◊━'
#           Use '\n' within the passed message to create a multi-line
#           banner. The leading space used on the first line of the
#           message is mirrored to the end of the string for single
#           and multiline banner messages.

#           Various banner line characters:
#           Note: Some chars are wider than standard text
#           ----------------------------------------------
#           * ⎯ ─ ━ ┉ ┈ ═ ═ = - _ [ ] ■ □ ▢ ▣ ▤ ▥ ▦ ▧ ▨ ▩
#           ▪ ▫ ▬ ▭ ▱ ▰ ▁ ▂ ▃ ▄ ▅ ▆ ▇ █ ╱ ╲ ◎ ◊ ◆ ◈ ◯
#           ▏ ▎ ▍ ▌ ▋ ▊ ▉ █
def max_line_len(msg: str) -> int:
  max_len = 0
  line1_space_len = len(msg) - len(msg.lstrip())
  if len(msg):
    not_line_one = 0

    for line in msg.splitlines():
      if not_line_one:
        line_x_space_len = len(line) - len(line.lstrip())
      else:
        line_x_space_len = 0
      white_space_add = (not_line_one * line1_space_len) + line1_space_len + line_x_space_len

      # A bit of a hack...If a non-line #1 is all white space, it gets added as if it was an
      # indent and makes the border lines really long. For now ignore all "white-space" lines
      # by limiting the indent to 4.
      if white_space_add > 4:
        white_space_add = line1_space_len
      if max_len < len(line) + white_space_add:
        max_len = len(line) + white_space_add
      not_line_one = 1
    return max_len

def banner(banner_msg: str, line_char: str = '─') -> None:
  """
  Prints a string message with an upper & lower character border
  Supports multi-line banners. If leading space is supplied on
  the first line, that space indents subsequent lines. Leading
  space is also mirrored to the end of the message lines.
  :param banner_msg: Required string to display
  :param line_char: [OPT] Single or multi-char border. [DEF] = '─'
  :return: Nothing
  """
  banner_len = max_line_len(banner_msg)
  lead_space = (len(banner_msg) - len(banner_msg.lstrip())) * ' '
  line_char_len = len(line_char)
  line = (line_char * int(banner_len / line_char_len) + line_char)[:banner_len]

  if banner_len:
    if line_char != '':
      print(f'{line}', flush=True)
    line_one = True
    for msg_line in banner_msg.splitlines():
      if line_one:
        print(f'{lead_space}{msg_line.lstrip()}', flush=True)
        line_one = False
      else:
        print(f'{lead_space}{msg_line}', flush=True)
    if line_char != '':
      print(f'{line}', flush=True)
          
def dbg_banner(msg: str, *args: any) -> None:
  """
  Override of a regular banner except it adds
  'DBG:' to the message and changes the default
  line character to '■'.
  """
  message = msg
  for num in args:
    message = message + ' ' + str(num)
  banner('DBG: ' + message, '■')


# Test
if __name__ == "__main__":
  border_list = ['*', '⎯', '─', '━', '┉', '┈', '═', '═',
                 '=', '-', '_', '[]', '■', '□', '▢', '▣',
                 '▤', '▥', '▦', '▧', '▨', '▩', '▪', '▫',
                 '▬', '▭', '▱', '▰', '╱ ╲', '◎', '◊', '◆',
                 '◈', '◯', '━◊━', 'v', 'w', 'x', 'X']
  print('\n' * 2, flush=True)
  hdr = f' col1      col2         col3           col4      col5          col6'
  dat = f"                                                                  "
  rsp = f'^^^^      ^^^^         ^^^^           ^^^^      ^^^^          ^^^^'
  print(f'{len(hdr)}, {len(hdr)}, {len(rsp)}', flush=True)
  banner(f'{hdr}\n{dat}\n{rsp}\n')
  banner(f'{hdr}\n{rsp}\n')

  # exit(0)

  banner(" Default Banner\nMultiline\nBorder char NOT specified\n  Extra long indented Variable: 10\n  Status: Ok")
  print("\n", flush=True)
  banner("    Default Banner\nMultiline\nWith Mirrored\nLeading & Lagging\nWhite space\n  Variable: 10\n  Status: Ok")
  print("\n", flush=True)
  banner(" Default Banner - border char NOT specified")
  print("\n", flush=True)

  dbg_banner(" Ima\nMultiline\nDebug\nBanner")
  print("\n", flush=True)

  dbg_banner(" Ima Debug Banner")
  print("\n", flush=True)

  for type in border_list:
    banner(f'  Im-a-banner with "{type}" border\nIma longer second line as a test', type)
    print("\n", flush=True)