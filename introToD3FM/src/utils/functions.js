export function getTrueKeys(obj) {
  const trueKeys = [];
  for (const [key, value] of Object.entries(obj)) {
    if (value === true) {
      trueKeys.push(key);
    }
  }
  return trueKeys;
}


export function formatDataForTimeline(startDate, endDate, data) {
  // Convert date strings to the desired format using map
  const formattedData = data.map((item) => ({
    ...item,
    date: `${item.date.getUTCFullYear()}, ${item.date.getUTCMonth() + 1}, ${item.date.getUTCDate()}`,
  }));

  // Format startDate and endDate
  const formattedStartDate = `${startDate.getUTCFullYear()}, ${startDate.getUTCMonth() + 1}, ${startDate.getUTCDate()}`;
  const formattedEndDate = `${endDate.getUTCFullYear()}, ${endDate.getUTCMonth() + 1}, ${endDate.getUTCDate()}`;

  // Convert formattedStartDate and formattedEndDate to Date objects
  const startDateF = new Date(formattedStartDate);
  const endDateF = new Date(formattedEndDate);

  // Convert date strings in formattedData back to Date objects
  const dataF = formattedData.map((item) => ({
    ...item,
    date: new Date(item.date),
  }));

  return {
    startDate: startDateF,
    endDate: endDateF,
    formattedData: dataF,
  };
}