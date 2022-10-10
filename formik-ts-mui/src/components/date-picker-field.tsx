// PLUGINS IMPORTS //
import React, { useState, useEffect } from "react";
import { useField } from "formik";
import Grid from "@material-ui/core/Grid";
import {
  MuiPickersUtilsProvider,
  KeyboardDatePicker,
} from "@material-ui/pickers";
import DateFnsUtils from "@date-io/date-fns";
import Moment from "moment";

// COMPONENTS IMPORTS //

// EXTRA IMPORTS //

/////////////////////////////////////////////////////////////////////////////

const DatePickerField = (props: any) => {
  const [field, meta, helper] = useField(props);
  const { touched, error } = meta;
  const { setValue } = helper;
  const isError = touched && error && true;
  const { value } = field;
  const [selectedDate, setSelectedDate] = useState(props.value);
  const { isEditableProps } = props;

  useEffect(() => {
    if (value) {
      const date = new Date(value);
      console.log("data in useEffect ", date);
      setSelectedDate(date);
    }
  }, [value]);

  function _onChange(date: any) {
    const formattedDate = Moment(date).format("DD/MM/YYYY");
    // console.log("datepicker date", date);
    // console.log("datepicker formattedDate", formattedDate);
    if (formattedDate) {
      setSelectedDate(formattedDate);
      try {
        setValue(formattedDate);
      } catch (error) {
        setValue(formattedDate);
      }
    } else {
      setValue(formattedDate);
    }
  }

  return (
    <Grid container>
      <MuiPickersUtilsProvider utils={DateFnsUtils}>
        <KeyboardDatePicker
          {...field}
          {...props}
          value={selectedDate}
          onChange={_onChange}
          disabled={!isEditableProps}
          error={isError}
          invalidDateMessage={isError && error}
          helperText={isError && error}
        />
      </MuiPickersUtilsProvider>
    </Grid>
  );
};

export default DatePickerField;
